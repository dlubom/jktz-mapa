import ImageLayer from 'ol/layer/Image.js';
import ImageCanvasSource from 'ol/source/ImageCanvas.js';
import type Map from 'ol/Map.js';
import {eligiblePlans} from './catalog.ts';
import {ImagePool} from './resources.ts';
import type {PlanEntry, Extent} from './types.ts';

type Draw = {url:string; extent:Extent; gutter:number};
export class Plans {
  selected=new Set<string>();
  hidden=new Set<string>();
  private wholePreview=new globalThis.Map<string,number>();
  opacity=new globalThis.Map<string,number>();
  order:string[]=[];
  enabled=true;
  focusId:string|null=null;
  isolated=false;
  private canvas=document.createElement('canvas');
  private source:ImageCanvasSource;
  layer:ImageLayer<ImageCanvasSource>;
  pool:ImagePool;
  active:string[]=[];
  reduced=false;
  private plans:PlanEntry[];
  private map:Map;
  private report:()=>void;
  fitPadding:()=>number[];
  private reportQueued=false;
  private disposed=false;
  constructor(map:Map,plans:PlanEntry[],report:()=>void,fitPadding:()=>number[]=()=>[35,35,35,35]){
    this.map=map;this.plans=plans;this.report=report;this.fitPadding=fitPadding;this.order=plans.map(p=>p.id);
    this.pool=new ImagePool(6,64*1024*1024,undefined,()=>{this.source.changed();report();});
    this.source=new ImageCanvasSource({projection:'EPSG:2180',ratio:1,canvasFunction:(extent,resolution,pixelRatio,size)=>this.render(extent as Extent,resolution,pixelRatio,size)});
    this.layer=new ImageLayer({source:this.source,zIndex:5});map.addLayer(this.layer);
  }
  private draws(plan:PlanEntry,extent:Extent,resolution:number):Draw[]{
    if(resolution>1 || !plan.levels.length || resolution >= plan.nativeResolution*2**plan.levels.length){
      return [{url:plan.preview.url,extent:plan.preview.extent||plan.extent,gutter:0}];
    }
    const levels=[...plan.levels].sort((a,b)=>a.resolution-b.resolution);
    let level=levels[0];
    for(const candidate of levels) if(candidate.resolution<=resolution)level=candidate;
    const step=plan.tileSize*level.resolution;
    const startX=Math.max(0,Math.floor((extent[0]-plan.extent[0])/step));
    const endX=Math.min(level.columns-1,Math.floor((extent[2]-plan.extent[0])/step));
    const startY=Math.max(0,Math.floor((plan.extent[3]-extent[3])/step));
    const endY=Math.min(level.rows-1,Math.floor((plan.extent[3]-extent[1])/step));
    const out:Draw[]=[];
    for(let x=startX;x<=endX;x++)for(let y=startY;y<=endY;y++){
      const left=plan.extent[0]+x*step,top=plan.extent[3]-y*step;
      out.push({url:plan.tileUrl.replace('{level}',String(level.level)).replace('{x}',String(x)).replace('{y}',String(y)),extent:[left,top-step,left+step,top],gutter:plan.gutter||0});
    }
    return out;
  }
  private render(extent:Extent,resolution:number,pixelRatio:number,size:number[]):HTMLCanvasElement {
    const previousActive=this.active,previousReduced=this.reduced;
    this.canvas.width=Math.round(size[0]);this.canvas.height=Math.round(size[1]);
    const ctx=this.canvas.getContext('2d')!;
    if(!this.enabled){this.pool.clear();this.active=[];this.reduced=false;this.reportAfterRender(previousActive,previousReduced);return this.canvas;}
    const eligible=eligiblePlans(this.plans,extent,resolution,this.selected,this.hidden)
      .filter(plan=>!this.isolated||plan.id===this.focusId);
    eligible.sort((a,b)=>this.order.indexOf(a.id)-this.order.indexOf(b.id));
    this.active=eligible.map(p=>p.id);
    // Use CSS scale for eligibility, actual device pixels for detail. A shared budget
    // reduces detail uniformly, never silently drops a fixed number of plans.
    let detailResolution=resolution/pixelRatio;
    for(const [id,fitResolution] of this.wholePreview)if(resolution<fitResolution*.95)this.wholePreview.delete(id);
    const makeDraws=()=>eligible.map(p=>this.wholePreview.has(p.id)?[{url:p.preview.url,extent:p.preview.extent||p.extent,gutter:0}]:this.draws(p,extent,resolution>1?resolution:detailResolution));
    let drawLists=makeDraws();
    let estimate=()=>drawLists.reduce((sum,list)=>sum+list.length*514*514*4,0);
    this.reduced=false;
    for(let i=0;estimate()>48*1024*1024&&i<16;i++){
      detailResolution*=2;this.reduced=true;
      drawLists=makeDraws();
    }
    const wanted=drawLists.flat().map(d=>d.url);this.pool.want(wanted);
    const scale=pixelRatio/resolution;
    eligible.forEach((plan,index)=>{
      // Each cropped tile covers only its own cell; preserve the source white background.
      ctx.globalAlpha=this.opacity.get(plan.id)??.75;
      for(const draw of drawLists[index]){
        const bitmap=this.pool.get(draw.url);if(!bitmap)continue;
        const [left,bottom,right,top]=draw.extent;
        const g=draw.gutter;
        ctx.drawImage(bitmap,g,g,bitmap.width-2*g,bitmap.height-2*g,(left-extent[0])*scale,(extent[3]-top)*scale,(right-left)*scale,(top-bottom)*scale);
      }
    });
    ctx.globalAlpha=1;
    this.reportAfterRender(previousActive,previousReduced);
    return this.canvas;
  }
  private reportAfterRender(previousActive:string[],previousReduced:boolean){
    if(previousReduced===this.reduced&&previousActive.length===this.active.length&&previousActive.every((id,i)=>id===this.active[i]))return;
    if(this.reportQueued)return;
    this.reportQueued=true;
    // Reporting after the canvas callback keeps UI changes outside the draw and
    // also updates status when all requested bitmaps came from the cache.
    queueMicrotask(()=>{this.reportQueued=false;if(!this.disposed)this.report();});
  }
  refresh(){this.source.changed();this.report();}
  setIsolation(enabled:boolean){this.isolated=enabled&&this.focusId!==null;this.refresh();}
  endFocus(){this.isolated=false;this.focusId=null;this.refresh();}
  toggle(id:string,visible:boolean){
    if(visible){this.hidden.delete(id);this.selected.add(id);if(!this.order.includes(id))this.order.push(id);}
    else{this.hidden.add(id);this.selected.delete(id);if(this.focusId===id){this.endFocus();return;}}
    this.refresh();
  }
  show(plan:PlanEntry){
    this.focusId=plan.id;
    this.order=this.order.filter(id=>id!==plan.id).concat(plan.id);
    this.enabled=true;this.layer.setVisible(true);
    // Report focus before fitting so the toolbar can provide its current padding.
    this.toggle(plan.id,true);
    this.fit(plan);
  }
  fit(plan:PlanEntry){
    this.map.getView().cancelAnimations();
    this.map.getView().fit(plan.preview.extent||plan.extent,{padding:this.fitPadding(),duration:0,maxZoom:24});
    this.wholePreview.set(plan.id,this.map.getView().getResolution()!);
    this.refresh();
  }
  move(id:string,direction:number){if(!this.order.includes(id))this.order.push(id);const i=this.order.indexOf(id),j=Math.max(0,Math.min(this.order.length-1,i+direction));[this.order[i],this.order[j]]=[this.order[j],this.order[i]];this.refresh();}
  dispose(){this.disposed=true;this.pool.dispose();this.layer.dispose();this.source.dispose();this.canvas.width=this.canvas.height=0;}
}
