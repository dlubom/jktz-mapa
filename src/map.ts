import Map from 'ol/Map.js';
import View from 'ol/View.js';
import TileLayer from 'ol/layer/Tile.js';
import VectorLayer from 'ol/layer/Vector.js';
import VectorSource from 'ol/source/Vector.js';
import XYZ from 'ol/source/XYZ.js';
import TileWMS from 'ol/source/TileWMS.js';
import {createXYZ} from 'ol/tilegrid.js';
import OSM from 'ol/source/OSM.js';
import GeoJSON from 'ol/format/GeoJSON.js';
import Feature from 'ol/Feature.js';
import Point from 'ol/geom/Point.js';
import {Circle, Fill, Stroke, Style, Text} from 'ol/style.js';
import {defaults as controls, ScaleLine} from 'ol/control.js';
import {register} from 'ol/proj/proj4.js';
import proj4 from 'proj4';
import {transformExtent} from 'ol/proj.js';
import TileState from 'ol/TileState.js';
import {unByKey} from 'ol/Observable.js';
import {listen} from 'ol/events.js';
import {calculateSourceExtentResolution} from 'ol/reproj.js';
import type Tile from 'ol/Tile.js';
import type {EventsKey} from 'ol/events.js';
import {intersects, readJson} from './catalog.ts';
import {basemapDefinition,basemapStatus,BasemapFailures,type BasemapTile,type BasemapStatusInput} from './basemaps.ts';
import {Plans} from './plans.ts';
import type {Catalog, Extent, ModelEntry, Coordinate} from './types.ts';

proj4.defs('EPSG:2180','+proj=tmerc +lat_0=0 +lon_0=19 +k=0.9993 +x_0=500000 +y_0=-5300000 +ellps=GRS80 +units=m +no_defs');register(proj4);
const white=new Fill({color:'#fff'});
const pointStyle=(color:string,radius:number)=>new Style({image:new Circle({radius,fill:new Fill({color}),stroke:new Stroke({color:'#fff',width:1.5})})});
type BasemapSource=XYZ|TileWMS|OSM;
interface TrackedTile {tile:Tile;extent:Extent;zoom:number;listener?:EventsKey}
interface BasemapTracking {source:BasemapSource;tiles:globalThis.Map<string,TrackedTile>;failures:BasemapFailures;listeners:EventsKey[]}
export class MapController {
  map:Map;plans:Plans;
  osm=new TileLayer({source:new OSM(),zIndex:0});
  tpn=new TileLayer<XYZ|TileWMS>({zIndex:1,maxResolution:6});
  best:VectorLayer; other:VectorLayer; rejected:VectorLayer; differences:VectorLayer;
  modelsEnabled=true;hiddenModels=new Set<string>();
  selectedId:string|null=null;
  private allNames=false;
  private modelLayers=new globalThis.Map<string,VectorLayer>();
  private modelRequests=new globalThis.Map<string,AbortController>();
  private catalog:Catalog;
  private report:(message:string,kind:string)=>void;
  private tpnTimer:ReturnType<typeof setTimeout>|undefined;
  private tpnRetries=0;
  private tpnName='rgb_2020';
  private basemapOpacity=1;
  private osmTracking?:BasemapTracking;
  private tpnTracking?:BasemapTracking;
  private basemapFrame:number|undefined;
  private basemapViewKey='';
  private basemapMessages={status:'',warning:''};
  private disposed=false;
  private measurements?:Promise<void>;
  private differenceRequest?:Promise<void>;
  private format=new GeoJSON();
  constructor(catalog:Catalog,select:(ids:string[])=>void,coordinates:(c:Coordinate)=>void,report:(message:string,kind:string)=>void,planReport:()=>void){
    this.catalog=catalog;this.report=report;
    const features=catalog.objects.filter(o=>o.coordinate).map(o=>new Feature({geometry:new Point(o.coordinate!),objectId:o.id,name:o.name}));
    this.best=new VectorLayer({source:new VectorSource({features}),zIndex:30,declutter:true,renderOrder:(a,b)=>Number(b.get('objectId')===this.selectedId)-Number(a.get('objectId')===this.selectedId),style:feature=>{
      const active=feature.get('objectId')===this.selectedId;
      return new Style({image:new Circle({radius:active?7:4,declutterMode:'none',fill:new Fill({color:active?'#e56f35':'#12675a'}),stroke:new Stroke({color:'#fff',width:1.5})}),text:new Text({text:feature.get('name'),declutterMode:this.allNames?'none':active?'obstacle':'declutter',padding:[2,4,2,4],font:`${active?'700':'500'} 11px system-ui`,offsetY:-13,fill:new Fill({color:active?'#873a13':'#183d35'}),stroke:new Stroke({color:'rgba(255,255,255,.95)',width:3}),overflow:true})});
    }});
    this.other=new VectorLayer({source:new VectorSource(),zIndex:25,visible:false,style:pointStyle('#3972b0',4)});
    this.rejected=new VectorLayer({source:new VectorSource(),zIndex:26,visible:false,style:pointStyle('#b44956',5)});
    this.differences=new VectorLayer({source:new VectorSource(),zIndex:15,visible:false,style:feature=>new Style({stroke:new Stroke({color:'#bd6b35',width:1.5,lineDash:[5,4]}),text:new Text({text:`${Number(feature.get('differenceM')||0).toLocaleString('pl-PL',{maximumFractionDigits:1})} m`,font:'11px system-ui',fill:new Fill({color:'#783e1f'}),stroke:new Stroke({color:'#fff',width:3})})})});
    this.map=new Map({target:'map',layers:[this.osm,this.tpn,this.differences,this.other,this.rejected,this.best],view:new View({projection:'EPSG:2180',center:[567000,154000],resolution:25,minResolution:.025,maxResolution:300}),controls:controls({rotate:false,zoomOptions:{zoomInTipLabel:'Przybliż',zoomOutTipLabel:'Oddal'},attributionOptions:{collapsible:false}}).extend([new ScaleLine({units:'metric'})]),maxTilesLoading:6});
    this.osmTracking=this.trackBasemapSource(this.osm.getSource()!);
    this.plans=new Plans(this.map,catalog.plans,planReport);
    this.map.on('singleclick',event=>{const ids=new Set<string>();this.map.forEachFeatureAtPixel(event.pixel,f=>{if(f.get('objectId'))ids.add(f.get('objectId'));},{hitTolerance:8,layerFilter:l=>[this.best,this.other,this.rejected].includes(l as VectorLayer)});if(ids.size)select([...ids]);});
    this.map.on('pointermove',event=>{coordinates(event.coordinate as Coordinate);this.map.getTargetElement()!.style.cursor=this.map.hasFeatureAtPixel(event.pixel,{layerFilter:l=>[this.best,this.other,this.rejected].includes(l as VectorLayer)})?'pointer':'';});
    this.map.on('moveend',()=>{this.updateModels();this.refreshBasemapStatus();coordinates(this.map.getView().getCenter() as Coordinate);planReport();});
    this.map.getView().on(['change:resolution','change:center'],()=>this.scheduleBasemapStatus());
    this.map.on('change:size',()=>this.scheduleBasemapStatus());
    this.map.getView().fit(catalog.extent,{padding:[45,45,45,45]});this.setBasemap('rgb_2020');this.updateModels();
  }
  setAllNames(visible:boolean){this.allNames=visible;this.best.changed();}
  setBasemap(name:string,automatic=false){
    name=basemapDefinition(name).id;
    clearTimeout(this.tpnTimer);this.tpnTimer=undefined;if(!automatic)this.tpnRetries=0;this.tpnName=name;
    const old=this.tpn.getSource();
    this.releaseBasemapTracking(this.tpnTracking);this.tpnTracking=undefined;
    this.tpn.setVisible(name!=='osm');
    this.osm.setOpacity(name==='osm'?this.basemapOpacity:1);
    if(name==='osm'){this.tpn.setSource(null);old?.dispose();this.refreshBasemapStatus();return;}
    const geology=name==='smgt_a_zakryta'||name==='smgt_b_odkryta';
    const source=geology?new TileWMS({
      url:`https://cbdgmapa.pgi.gov.pl/arcgis/services/kartografia/${name}/MapServer/WMSServer`,
      // WMS 1.1.1 keeps easting/northing; 1.3.0 uses northing/easting for EPSG:2180.
      params:{LAYERS:name==='smgt_a_zakryta'?'0,1,2,3,4,5':'0,1,2,3,4',VERSION:'1.1.1',FORMAT:'image/png',TRANSPARENT:true},
      projection:'EPSG:2180',hidpi:false,wrapX:false,transition:0,
      // SMGT is visible below scale 1:23623 (~6.6 m/px); keep every tile within it.
      tileGrid:createXYZ({extent:[0,0,1000000,1000000],maxResolution:6,maxZoom:10}),
      attributions:'© <a href="https://baza.pgi.gov.pl/cbdg/geoportal/uslugi/gis" target="_blank" rel="noopener">PIG-PIB · SMGT 1:10 000</a>'
    }):new XYZ({url:`https://tpn.obliview.com/Data/${name}/{z}/{x}/{y}.jpg`,minZoom:15,maxZoom:20,projection:'EPSG:3857',wrapX:false,transition:0,attributions:'© <a href="https://tpn.gov.pl/" target="_blank" rel="noopener">Tatrzański Park Narodowy</a> / Obliview'});
    this.tpn.setExtent(basemapDefinition(name).extent);
    this.tpnTracking=this.trackBasemapSource(source);
    this.tpn.setSource(source);this.tpn.setOpacity(this.basemapOpacity);old?.dispose();this.refreshBasemapStatus();
  }
  setBasemapOpacity(value:number){this.basemapOpacity=Math.max(0,Math.min(1,value));this.tpn.setOpacity(this.basemapOpacity);this.osm.setOpacity(this.tpnName==='osm'?this.basemapOpacity:1);this.refreshBasemapStatus();}
  private scheduleBasemapStatus(){if(this.disposed||this.basemapFrame!==undefined)return;this.basemapFrame=requestAnimationFrame(()=>{this.basemapFrame=undefined;this.refreshBasemapStatus();});}
  private trackBasemapSource(source:BasemapSource):BasemapTracking {
    const tracking:BasemapTracking={source,tiles:new globalThis.Map(),failures:new BasemapFailures(),listeners:[]};
    const active=()=>!this.disposed&&(this.osmTracking===tracking||this.tpnTracking===tracking);
    const getTile=source.getTile.bind(source);
    // Track target tiles too: source load events alone can precede completion of
    // EPSG:2180 reprojection, or report success with missing source tiles.
    source.getTile=(z,x,y,pixelRatio,projection,cache)=>{
      const tile=getTile(z,x,y,pixelRatio,projection,cache);
      if(projection===this.map.getView().getProjection()){
        const key=tile.getTileCoord().join('/'),old=tracking.tiles.get(key);
        if(old?.tile!==tile){
          if(old?.listener)unByKey(old.listener);
          tracking.tiles.set(key,{tile,zoom:z,extent:source.getTileGridForProjection(projection).getTileCoordExtent(tile.getTileCoord()) as Extent,listener:listen(tile,'change',()=>{
            // Renderer cache hits bypass source.getTile(). Keep offscreen tiles
            // until OL releases them; EMPTY is the cache-eviction signal.
            if(tile.getState()===TileState.EMPTY&&tracking.tiles.get(key)?.tile===tile){const entry=tracking.tiles.get(key)!;if(entry.listener)unByKey(entry.listener);tracking.tiles.delete(key);}
            if(active())this.scheduleBasemapStatus();
          })});
          if(active())this.scheduleBasemapStatus();
        }
      }
      return tile;
    };
    tracking.listeners.push(source.on('tileloaderror',event=>{
      if(!active())return;
      const coordinate=event.tile.getTileCoord();
      tracking.failures.record(coordinate.join('/'),transformExtent(source.getTileGridForProjection(source.getProjection()!).getTileCoordExtent(coordinate),source.getProjection()!,this.map.getView().getProjection(),8) as Extent,coordinate[0]);
      this.scheduleBasemapStatus();
    }),source.on('tileloadend',event=>{if(active()){tracking.failures.recover(event.tile.getTileCoord().join('/'));this.scheduleBasemapStatus();}}));
    return tracking;
  }
  private releaseBasemapTracking(tracking?:BasemapTracking){if(!tracking)return;unByKey(tracking.listeners);for(const entry of tracking.tiles.values())if(entry.listener)unByKey(entry.listener);tracking.tiles.clear();tracking.failures.clear();}
  private basemapTiles(tracking:BasemapTracking,extent:Extent){
    const view=this.map.getView(),projection=view.getProjection(),grid=tracking.source.getTileGridForProjection(projection),zoom=grid.getZForResolution(view.getResolution()!,tracking.source.zDirection),tiles:BasemapTile[]=[];
    const nativeGrid=tracking.source.getTileGridForProjection(tracking.source.getProjection()!),nativeZooms=new Set<number>();
    for(const entry of tracking.tiles.values()){
      if(entry.zoom!==zoom||!intersects(entry.extent,extent))continue;
      const state=entry.tile.getState();tiles.push({extent:entry.extent,zoom,state:state===TileState.LOADED?'loaded':state===TileState.ERROR?'error':state===TileState.EMPTY?'empty':'loading'});
      nativeZooms.add(nativeGrid.getZForResolution(calculateSourceExtentResolution(tracking.source.getProjection()!,projection,entry.extent,grid.getResolution(zoom))));
    }
    const sourceFailures=tracking.failures.current(extent,zoom,nativeZooms);
    return {zoom,tiles,sourceFailures};
  }
  refreshBasemapStatus(){
    if(this.disposed||!this.map.getSize())return;
    const view=this.map.getView(),resolution=view.getResolution()!,extent=view.calculateExtent(this.map.getSize()) as Extent;
    const viewKey=[resolution,...extent].map(n=>n.toFixed(2)).join('/');
    if(viewKey!==this.basemapViewKey){this.basemapViewKey=viewKey;this.tpnRetries=0;clearTimeout(this.tpnTimer);this.tpnTimer=undefined;}
    const osm=this.osmTracking?this.basemapTiles(this.osmTracking,extent):undefined;
    const osmLoaded=osm?.tiles.some(t=>t.state==='loaded'),osmFailed=!!osm?.sourceFailures.length||osm?.tiles.some(t=>t.state==='error'),osmLoading=!osm?.tiles.length||osm?.tiles.some(t=>t.state==='loading');
    const osmState:BasemapStatusInput['osmState']=osmLoaded?(osmFailed||osmLoading?'partial':'loaded'):osmFailed?'error':'loading';
    const selected=this.tpnTracking?this.basemapTiles(this.tpnTracking,extent):{zoom:0,tiles:[],sourceFailures:[]};
    const status=basemapStatus({id:this.tpnName,resolution,extent,opacity:this.basemapOpacity,...selected,osmState});
    if(status.message!==this.basemapMessages.status){this.basemapMessages.status=status.message;this.report(status.message,'basemap');}
    if(status.warning!==this.basemapMessages.warning){this.basemapMessages.warning=status.warning;this.report(status.warning,'tpn');}
    if(!status.warning){clearTimeout(this.tpnTimer);this.tpnTimer=undefined;}
    else if(this.tpnRetries<1&&!this.tpnTimer){const name=this.tpnName;this.tpnTimer=setTimeout(()=>{this.tpnTimer=undefined;if(this.disposed||name!==this.tpnName||viewKey!==this.basemapViewKey)return;this.tpnRetries++;this.setBasemap(name,true);},2000);}
  }
  retryBasemap(){this.setBasemap(this.tpnName);}
  select(id:string,zoom=true){this.selectedId=id;this.best.changed();const o=this.catalog.objects.find(x=>x.id===id);if(zoom&&o?.coordinate)this.map.getView().animate({center:o.coordinate,resolution:Math.min(this.map.getView().getResolution()!,1),duration:350});}
  async toggleMeasurements(role:'other'|'rejected',visible:boolean){
    this[role].setVisible(visible);if(!visible)return;
    this.measurements??=readJson('data/measurements.geojson').then(data=>{for(const feature of this.format.readFeatures(data,{dataProjection:'EPSG:2180',featureProjection:'EPSG:2180'})){const role:unknown=feature.get('role');if(role==='other'||role==='rejected')this[role].getSource()!.addFeature(feature);}this.report('','data');}).catch(error=>{this.measurements=undefined;throw error;});
    try{await this.measurements;}catch(error){this.report(`${error} Wyłącz i włącz warstwę, aby ponowić.`,'data');}
  }
  async toggleDifferences(visible:boolean){
    this.differences.setVisible(visible);if(!visible)return;
    this.differenceRequest??=readJson('data/differences.geojson').then(data=>{this.differences.getSource()!.addFeatures(this.format.readFeatures(data,{dataProjection:'EPSG:2180',featureProjection:'EPSG:2180'}));this.report('','data');}).catch(error=>{this.differenceRequest=undefined;throw error;});
    try{await this.differenceRequest;}catch(error){this.report(`${error} Wyłącz i włącz warstwę, aby ponowić.`,'data');}
  }
  updateModels(){
    const extent=this.map.getView().calculateExtent(this.map.getSize()) as Extent;
    const visible=this.catalog.models.filter(m=>this.modelsEnabled&&!this.hiddenModels.has(m.id)&&intersects(m.extent,extent));const ids=new Set(visible.map(m=>m.id));
    for(const [id,c] of this.modelRequests)if(!ids.has(id)){c.abort();this.modelRequests.delete(id);}
    for(const [id,l] of this.modelLayers)if(!ids.has(id)){this.map.removeLayer(l);l.getSource()?.clear();l.dispose();this.modelLayers.delete(id);}
    for(const model of visible)if(!this.modelLayers.has(model.id)&&!this.modelRequests.has(model.id))this.loadModel(model);
  }
  private async loadModel(model:ModelEntry){
    const controller=new AbortController();this.modelRequests.set(model.id,controller);
    try{const data=await readJson(model.url,controller.signal);if(controller.signal.aborted)return;
      const layer=new VectorLayer({source:new VectorSource({features:this.format.readFeatures(data,{dataProjection:'EPSG:2180',featureProjection:'EPSG:2180'})}),zIndex:10,style:new Style({stroke:new Stroke({color:'#9c3851',width:1.6})})});
      this.modelLayers.set(model.id,layer);this.map.addLayer(layer);
    }catch(error){if(!controller.signal.aborted)this.report(`Nie wczytano ciągu ${model.name}. Przesuń mapę, aby ponowić.`,'data');}
    finally{if(this.modelRequests.get(model.id)===controller)this.modelRequests.delete(model.id);}
  }
  fit(){this.map.getView().fit(this.catalog.extent,{padding:[40,40,40,40],duration:300});}
  dispose(){this.disposed=true;clearTimeout(this.tpnTimer);if(this.basemapFrame!==undefined)cancelAnimationFrame(this.basemapFrame);this.releaseBasemapTracking(this.osmTracking);this.releaseBasemapTracking(this.tpnTracking);for(const c of this.modelRequests.values())c.abort();this.plans.dispose();this.map.dispose();}
}
