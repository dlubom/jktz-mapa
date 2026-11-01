import type {Extent} from './types.ts';

export interface BasemapDefinition {
  id:string;
  label:string;
  provider:'TPN'|'PIG-PIB'|'OpenStreetMap';
  description:string;
  maxResolution?:number;
  extent?:Extent;
  legendUrl?:string;
}
const geology=(id:string,label:string,description:string):BasemapDefinition=>({
  id,label,provider:'PIG-PIB',description,maxResolution:6,
  // Service bounds in EPSG:2180, not a claim that every pixel contains geology.
  extent:[554473.3,144619.81,586394.36,163549.92],
  legendUrl:`https://cbdgmapa.pgi.gov.pl/arcgis/services/kartografia/${id}/MapServer/WMSServer?service=WMS&request=GetLegendGraphic&version=1.1.1&format=image/png&layer=0`
});
export const BASEMAPS:readonly BasemapDefinition[]=[
  {id:'rgb_2020',label:'Zdjęcia lotnicze · 2020 · TPN',provider:'TPN',description:'Ortofotomapa z 2020 r. Zdjęcia lotnicze w naturalnych kolorach.',maxResolution:6},
  {id:'rgb_2018',label:'Zdjęcia lotnicze · 2018 · TPN',provider:'TPN',description:'Ortofotomapa z 2018 r. Zdjęcia lotnicze w naturalnych kolorach.',maxResolution:6},
  {id:'NMT',label:'Rzeźba terenu · TPN · NMT',provider:'TPN',description:'Obraz numerycznego modelu terenu: rzeźba gruntu. Bez odczytu wysokości.',maxResolution:6},
  {id:'nmpt',label:'Pokrycie terenu · TPN · NMPT',provider:'TPN',description:'Obraz numerycznego modelu pokrycia terenu: m.in. roślinność i zabudowa. Bez odczytu wysokości.',maxResolution:6},
  geology('smgt_a_zakryta','Geologia zakryta · PIG-PIB · 1:10 000','Szczegółowa Mapa Geologiczna Tatr (SMGT), z osadami powierzchniowymi. Legenda opisuje kolory i wydzielenia.'),
  geology('smgt_b_odkryta','Geologia odkryta · PIG-PIB · 1:10 000','Szczegółowa Mapa Geologiczna Tatr (SMGT), podłoże skalne bez osadów powierzchniowych. Legenda opisuje kolory i wydzielenia.'),
  {id:'osm',label:'Mapa · OpenStreetMap',provider:'OpenStreetMap',description:'Mapa topograficzna OpenStreetMap. Stanowi też tło pod pozostałymi podkładami.'}
];
export const basemapDefinition=(id:string):BasemapDefinition=>BASEMAPS.find(b=>b.id===id)||BASEMAPS[0];

export interface BasemapTile {
  extent:Extent;
  zoom:number;
  state:'loading'|'loaded'|'error'|'empty';
}
export interface BasemapStatusInput {
  id:string;
  resolution:number;
  extent:Extent;
  opacity:number;
  zoom:number;
  tiles:readonly BasemapTile[];
  sourceFailures?:readonly BasemapTile[];
  osmState?:'loaded'|'partial'|'loading'|'error';
}
export interface BasemapStatus {
  actual:'none'|'osm'|'selected'|'mixed'|'loading';
  reason:'selected'|'scale'|'opacity'|'coverage'|'partial-coverage'|'loading'|'error'|'empty';
  message:string;
  warning:string;
}
const overlaps=(a:Extent,b:Extent)=>a[0]<b[2]&&a[2]>b[0]&&a[1]<b[3]&&a[3]>b[1];
const contains=(a:Extent,b:Extent)=>a[0]<=b[0]&&a[1]<=b[1]&&a[2]>=b[2]&&a[3]>=b[3];

/** Keep only coordinates of failed native tiles, without retaining images.
 * Reprojection can cache a LOADED target with gaps; panning away must not erase
 * those gaps. A successful reload or changing the source clears them. */
export class BasemapFailures {
  private tiles=new Map<string,{extent:Extent;zoom:number}>();
  record(key:string,extent:Extent,zoom:number){this.tiles.set(key,{extent,zoom});}
  recover(key:string){this.tiles.delete(key);}
  current(extent:Extent,targetZoom:number,nativeZooms:ReadonlySet<number>):BasemapTile[]{return [...this.tiles.values()].filter(t=>nativeZooms.has(t.zoom)&&overlaps(t.extent,extent)).map(t=>({extent:t.extent,zoom:targetZoom,state:'error'}));}
  clear(){this.tiles.clear();}
}

/** Describe only the current view. An XYZ load error alone cannot distinguish
 * missing TPN coverage from a network/service error. These tile URLs provide no
 * verified coverage polygon to this client; their envelope is not a substitute. */
export function basemapStatus(input:BasemapStatusInput):BasemapStatus {
  const definition=basemapDefinition(input.id),prefix=`Wybrano: ${definition.label}. Widoczne: `;
  const osmState=input.osmState||'loading';
  const result=(actual:BasemapStatus['actual'],reason:BasemapStatus['reason'],text:string,warning=''):BasemapStatus=>{
    if(osmState!=='loaded'){
      const fallback=osmState==='partial'?'częściowo OpenStreetMap':osmState==='error'?'brak podkładu (kafle OpenStreetMap niedostępne)':'brak gotowego podkładu (OpenStreetMap: wczytywanie)';
      if(text.startsWith('OpenStreetMap'))text=text.replace('OpenStreetMap',fallback);
      else text=text.replace(/ (?:i|nad) OpenStreetMap/,`; ${osmState==='partial'?'częściowo OpenStreetMap':`zapasowy OpenStreetMap: ${osmState==='error'?'kafle niedostępne':'wczytywanie'}`}`);
      if(actual==='osm')actual=osmState==='error'?'none':osmState==='partial'?'osm':'loading';
      if(warning)warning=warning.replace('W lukach widoczny jest OSM.',osmState==='error'?'Podkład zapasowy OSM także jest niedostępny.':osmState==='partial'?'OSM jest dostępny częściowo.':'Trwa wczytywanie zapasowego OSM.');
    }
    return {actual,reason,message:prefix+text,warning};
  };
  if(definition.id==='osm')return input.opacity===0?result('none','opacity','brak podkładu — krycie wybranego podkładu wynosi 0%.'):result('osm','selected',`OpenStreetMap${input.opacity<1?` (krycie ${Math.round(input.opacity*100)}%)`:''}.`);
  if(input.opacity===0)return result('osm','opacity','OpenStreetMap — krycie wybranego podkładu wynosi 0%.');
  if(definition.maxResolution!==undefined&&input.resolution>=definition.maxResolution)return result('osm','scale','OpenStreetMap — przybliż, aby zobaczyć wybrany podkład.');
  if(definition.extent&&!overlaps(definition.extent,input.extent))return result('osm','coverage','OpenStreetMap — poza zasięgiem wybranego podkładu.');
  const current=(tiles:readonly BasemapTile[])=>tiles.filter(t=>t.zoom===input.zoom&&overlaps(t.extent,input.extent));
  const tiles=current(input.tiles),loaded=tiles.some(t=>t.state==='loaded'),loading=!tiles.length||tiles.some(t=>t.state==='loading');
  const failed=tiles.some(t=>t.state==='error')||current(input.sourceFailures||[]).length>0;
  const provider=definition.provider;
  if(failed){
    const warning=provider==='TPN'?'Brak części kafli TPN (brak pokrycia lub błąd pobierania). W lukach widoczny jest OSM.':'Część podkładu geologicznego PIG-PIB jest niedostępna. W lukach widoczny jest OSM.';
    return result(loaded?'mixed':'osm','error',`${loaded?`${provider} i OpenStreetMap`:'OpenStreetMap'} — ${provider==='TPN'?'brak kafli TPN: brak pokrycia lub błąd pobierania':'kafle PIG-PIB niedostępne'}.`,warning);
  }
  if(loading)return result(loaded?'mixed':'loading','loading',`${loaded?`${provider} i OpenStreetMap`:'OpenStreetMap'}; trwa wczytywanie ${provider}.`);
  if(!loaded)return result('osm','empty',`OpenStreetMap — w tym widoku brak obrazu ${provider}.`);
  const partial=!!definition.extent&&!contains(definition.extent,input.extent);
  if(partial)return result('mixed','partial-coverage',`${provider} i OpenStreetMap — częściowy zasięg wybranego podkładu.`);
  if(input.opacity<1)return result('mixed','selected',`${provider} i OpenStreetMap (krycie ${Math.round(input.opacity*100)}%).`);
  // WMS is transparent; a successful response is not proof of full pixel coverage.
  return result(provider==='PIG-PIB'?'mixed':'selected','selected',provider==='PIG-PIB'?'PIG-PIB nad OpenStreetMap.':`${provider}.`);
}
