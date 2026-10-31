import 'ol/ol.css';
import Map from 'ol/Map.js';
import View from 'ol/View.js';
import TileLayer from 'ol/layer/Tile.js';
import ImageLayer from 'ol/layer/Image.js';
import ImageStatic from 'ol/source/ImageStatic.js';
import XYZ from 'ol/source/XYZ.js';
import TileGrid from 'ol/tilegrid/TileGrid.js';
import Projection from 'ol/proj/Projection.js';
const q=new URLSearchParams(location.search), id=q.get('id')||'001197', mode=q.get('mode')||'preview';
const plans=await (await fetch('./samples.json')).json();
const plan=plans[id];
const projection=new Projection({code:'EPSG:2180',units:'m'});
const stats={id,mode,dpr:devicePixelRatio,loaded:0,failed:0,decodedPixels:0,renderComplete:0};
const view=new View({projection,center:[(plan.extent[0]+plan.extent[2])/2,(plan.extent[1]+plan.extent[3])/2],resolution:Number(q.get('resolution')||.25)});
let source,layer;
if(mode==='preview'){
 source=new ImageStatic({url:`./rasters/${id}/preview-512.webp`,projection,imageExtent:plan.previewExtent});
 source.on('imageloadend',e=>{stats.loaded++;const i=e.image.getImage();stats.decodedPixels=i.width*i.height;});
 source.on('imageloaderror',()=>{stats.failed++;});
 layer=new ImageLayer({source,opacity:.75});
} else {
 const levels=[...plan.levels].reverse();
 const dpr=devicePixelRatio;
 const grid=new TileGrid({origin:[plan.extent[0],plan.extent[3]],resolutions:levels.map(l=>l.resolution*dpr),tileSize:512/dpr,sizes:levels.map(l=>[Math.ceil(l.width/512),Math.ceil(l.height/512)])});
 source=new XYZ({projection,tileGrid:grid,tilePixelRatio:dpr,wrapX:false,transition:0,
  tileUrlFunction:([z,x,y])=>`./rasters/${id}/tiles-512/${levels[z].level}/${x}-${y}.webp`,
  tileLoadFunction:(tile,url)=>{const im=new Image();im.onload=()=>{stats.loaded++;stats.decodedPixels+=512*512;const c=document.createElement('canvas');c.width=c.height=512;c.getContext('2d').drawImage(im,0,0);tile.setImage(c);};im.onerror=()=>{stats.failed++;tile.setState(3);};im.src=url;}});
 layer=new TileLayer({source,opacity:.75});
}
const map=new Map({target:'map',layers:[layer],view,maxTilesLoading:6});
if(mode==='preview')view.fit(plan.previewExtent,{size:map.getSize(),padding:[16,16,16,16]});
function snapshot(){return {...stats,resolution:view.getResolution(),viewport:map.getSize(),canvases:[...document.querySelectorAll('#map canvas')].map(c=>[c.width,c.height]),resources:performance.getEntriesByType('resource').filter(r=>r.name.endsWith('.webp')).map(r=>({url:r.name,bytes:r.encodedBodySize,duration:r.duration})),heap:performance.memory?.usedJSHeapSize??null};}
map.on('rendercomplete',()=>{stats.renderComplete++;document.querySelector('#metrics').textContent=JSON.stringify(snapshot(),null,2);});
window.rasterProbe={map,snapshot};
