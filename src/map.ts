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
import {intersects, readJson} from './catalog.ts';
import {Plans} from './plans.ts';
import type {Catalog, Extent, ModelEntry, Coordinate} from './types.ts';

proj4.defs('EPSG:2180','+proj=tmerc +lat_0=0 +lon_0=19 +k=0.9993 +x_0=500000 +y_0=-5300000 +ellps=GRS80 +units=m +no_defs');register(proj4);
const white=new Fill({color:'#fff'});
const pointStyle=(color:string,radius:number)=>new Style({image:new Circle({radius,fill:new Fill({color}),stroke:new Stroke({color:'#fff',width:1.5})})});
export class MapController {
  map:Map;plans:Plans;
  osm=new TileLayer({source:new OSM(),zIndex:0});
  tpn=new TileLayer<XYZ|TileWMS>({zIndex:1,maxResolution:6});
  best:VectorLayer; other:VectorLayer; rejected:VectorLayer; differences:VectorLayer;
  modelsEnabled=true;hiddenModels=new Set<string>();
  selectedId:string|null=null;
  private modelLayers=new globalThis.Map<string,VectorLayer>();
  private modelRequests=new globalThis.Map<string,AbortController>();
  private catalog:Catalog;
  private report:(message:string,kind:string)=>void;
  private tpnTimer:ReturnType<typeof setTimeout>|undefined;
  private tpnRetries=0;
  private tpnName='rgb_2020';
  private tpnFailures=new globalThis.Map<string,Extent>();
  private measurements?:Promise<void>;
  private differenceRequest?:Promise<void>;
  private format=new GeoJSON();
  constructor(catalog:Catalog,select:(ids:string[])=>void,coordinates:(c:Coordinate)=>void,report:(message:string,kind:string)=>void,planReport:()=>void){
    this.catalog=catalog;this.report=report;
    const features=catalog.objects.filter(o=>o.coordinate).map(o=>new Feature({geometry:new Point(o.coordinate!),objectId:o.id,name:o.name}));
    this.best=new VectorLayer({source:new VectorSource({features}),zIndex:30,declutter:false,style:feature=>{
      const active=feature.get('objectId')===this.selectedId;
      return new Style({image:new Circle({radius:active?7:4,fill:new Fill({color:active?'#e56f35':'#12675a'}),stroke:new Stroke({color:'#fff',width:1.5})}),text:new Text({text:feature.get('name'),font:`${active?'700':'500'} 12px system-ui`,offsetY:-13,fill:new Fill({color:active?'#873a13':'#183d35'}),stroke:new Stroke({color:'rgba(255,255,255,.95)',width:3}),overflow:true})});
    }});
    this.other=new VectorLayer({source:new VectorSource(),zIndex:25,visible:false,style:pointStyle('#3972b0',4)});
    this.rejected=new VectorLayer({source:new VectorSource(),zIndex:26,visible:false,style:pointStyle('#b44956',5)});
    this.differences=new VectorLayer({source:new VectorSource(),zIndex:15,visible:false,style:feature=>new Style({stroke:new Stroke({color:'#bd6b35',width:1.5,lineDash:[5,4]}),text:new Text({text:`${Number(feature.get('differenceM')||0).toLocaleString('pl-PL',{maximumFractionDigits:1})} m`,font:'11px system-ui',fill:new Fill({color:'#783e1f'}),stroke:new Stroke({color:'#fff',width:3})})})});
    this.map=new Map({target:'map',layers:[this.osm,this.tpn,this.differences,this.other,this.rejected,this.best],view:new View({projection:'EPSG:2180',center:[567000,154000],resolution:25,minResolution:.025,maxResolution:300}),controls:controls({rotate:false,zoomOptions:{zoomInTipLabel:'Przybliż',zoomOutTipLabel:'Oddal'},attributionOptions:{collapsible:false}}).extend([new ScaleLine({units:'metric'})]),maxTilesLoading:6});
    this.plans=new Plans(this.map,catalog.plans,planReport);
    this.map.on('singleclick',event=>{const ids=new Set<string>();this.map.forEachFeatureAtPixel(event.pixel,f=>{if(f.get('objectId'))ids.add(f.get('objectId'));},{hitTolerance:8,layerFilter:l=>[this.best,this.other,this.rejected].includes(l as VectorLayer)});if(ids.size)select([...ids]);});
    this.map.on('pointermove',event=>{coordinates(event.coordinate as Coordinate);this.map.getTargetElement()!.style.cursor=this.map.hasFeatureAtPixel(event.pixel,{layerFilter:l=>[this.best,this.other,this.rejected].includes(l as VectorLayer)})?'pointer':'';});
    this.map.on('moveend',()=>{this.updateModels();this.basemapWarning();coordinates(this.map.getView().getCenter() as Coordinate);planReport();});
    this.map.getView().fit(catalog.extent,{padding:[45,45,45,45]});this.setBasemap('rgb_2020');this.updateModels();
  }
  setBasemap(name:string,automatic=false){
    clearTimeout(this.tpnTimer);this.tpnTimer=undefined;if(!automatic)this.tpnRetries=0;this.tpnName=name;this.tpnFailures.clear();
    const old=this.tpn.getSource();
    this.tpn.setVisible(name!=='osm');this.report('','tpn');
    if(name==='osm'){this.tpn.setSource(null);old?.dispose();return;}
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
    this.tpn.setExtent(geology?[554473.3,144619.81,586394.36,163549.92]:undefined);
    source.on('tileloaderror',event=>{
      if(source!==this.tpn.getSource())return;
      const coordinate=event.tile.getTileCoord();this.tpnFailures.set(coordinate.join('/'),transformExtent(source.getTileGrid()!.getTileCoordExtent(coordinate),source.getProjection()!,'EPSG:3857') as Extent);this.basemapWarning();
      if(this.tpnRetries<1&&!this.tpnTimer)this.tpnTimer=setTimeout(()=>{this.tpnTimer=undefined;this.tpnRetries++;this.setBasemap(name,true);},2000);
    });
    source.on('tileloadend',event=>{if(source!==this.tpn.getSource())return;this.tpnFailures.delete(event.tile.getTileCoord().join('/'));this.basemapWarning();});
    this.tpn.setSource(source);old?.dispose();
  }
  private basemapWarning(){const extent=transformExtent(this.map.getView().calculateExtent(this.map.getSize()),'EPSG:2180','EPSG:3857') as Extent;const failed=this.tpnName!=='osm'&&this.map.getView().getResolution()!<6&&[...this.tpnFailures.values()].some(e=>intersects(e,extent));const provider=this.tpnName.startsWith('smgt_')?'geologicznego PIG-PIB':'TPN';this.report(failed?`Część podkładu ${provider} jest niedostępna. W lukach widoczny jest OSM.`:'','tpn');}
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
  dispose(){clearTimeout(this.tpnTimer);for(const c of this.modelRequests.values())c.abort();this.plans.dispose();this.map.dispose();}
}
