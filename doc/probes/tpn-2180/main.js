// Disposable browser experiment. No proxy, service worker or product importer.
import 'ol/ol.css';
import Map from 'ol/Map.js';
import View from 'ol/View.js';
import TileLayer from 'ol/layer/Tile.js';
import XYZ from 'ol/source/XYZ.js';
import OSM from 'ol/source/OSM.js';
import ImageTile from 'ol/source/ImageTile.js';
import {get, transform} from 'ol/proj.js';
import {register} from 'ol/proj/proj4.js';
import proj4 from 'proj4';

proj4.defs('EPSG:2180', '+proj=tmerc +lat_0=0 +lon_0=19 +k=0.9993 +x_0=500000 +y_0=-5300000 +ellps=GRS80 +units=m +no_defs');
register(proj4);
get('EPSG:2180').setExtent([100000,100000,900000,900000]);
const params = new URLSearchParams(location.search);
const mode = params.get('mode') || 'xyz';
const stats = {mode, started:0, loaded:0, failed:0, renderComplete:0, errors:[]};
addEventListener('error', e => stats.errors.push(e.message));
addEventListener('unhandledrejection', e => stats.errors.push(String(e.reason)));
const osm = new TileLayer({source:new OSM(),visible:false});
const tpn = new TileLayer({className:'tpn-canvas'});
const centerAt = (x,y,z=17) => transform([(x+0.5)/2**z*40075016.68557849-20037508.342789244,20037508.342789244-(y+0.5)/2**z*40075016.68557849], 'EPSG:3857','EPSG:2180');
const map = new Map({target:'map',layers:[osm,tpn],view:new View({projection:'EPSG:2180',center:centerAt(72811,44862),resolution:1,minResolution:0.05,maxResolution:30}),maxTilesLoading:6});
function snapshot(){return {...stats, projection:map.getView().getProjection().getCode(),center:map.getView().getCenter(),resolution:map.getView().getResolution(),dpr:devicePixelRatio,viewport:map.getSize(),canvases:[...document.querySelectorAll('canvas')].map(c=>[c.width,c.height]),crossOriginIsolated,online:navigator.onLine};}
function show(){document.querySelector('#metrics').textContent=JSON.stringify(snapshot(),null,2);}
function setSource(dataset){
  document.querySelector('#dataset').value=dataset;
  Object.assign(stats,{dataset,started:0,loaded:0,failed:0,renderComplete:0,errors:[]});
  document.querySelector('#status').textContent='';
  const options={url:`https://tpn.obliview.com/Data/${dataset}/{z}/{x}/{y}.jpg`,minZoom:15,maxZoom:20,projection:'EPSG:3857',wrapX:false,transition:0,attributions:'© Tatrzański Park Narodowy — podkład TPN / Obliview'};
  if(mode==='xyz-cors') options.crossOrigin='anonymous';
  const source=mode==='data' ? new ImageTile(options) : new XYZ(options);
  for(const [event,key] of [['tileloadstart','started'],['tileloadend','loaded'],['tileloaderror','failed']]) source.on(event,()=>{if(tpn.getSource()!==source)return;stats[key]++;if(key==='failed')document.querySelector('#status').textContent='Część podkładu TPN nie została wczytana. OSM jest dostępny pod spodem; spróbuj ponownie.';show();});
  tpn.setSource(source);
  show();
}
map.on('rendercomplete',()=>{stats.renderComplete++;show();});
map.on('moveend',show);
document.querySelector('#dataset').onchange=e=>setSource(e.target.value);
document.querySelector('#opacity').oninput=e=>tpn.setOpacity(Number(e.target.value));
document.querySelector('#osm').onchange=e=>osm.setVisible(e.target.checked);
document.querySelector('#known').onclick=()=>map.getView().setCenter(centerAt(72811,44862));
document.querySelector('#gap').onclick=()=>map.getView().setCenter(centerAt(72806,44888));
document.querySelector('#retry').onclick=()=>setSource(stats.dataset);
window.probe={map,tpn,osm,setSource,centerAt,snapshot};
setSource(params.get('dataset') || 'rgb_2020');
