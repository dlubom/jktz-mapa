import type {Catalog, CaveEntry, ObjectEntry, PlanEntry, Extent, Coordinate} from './types.ts';
export function normalize(value: string): string {
  return value.toLocaleLowerCase('pl').replaceAll('ł', 'l').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim();
}
export function searchCatalog(objects: ObjectEntry[], query: string): ObjectEntry[] {
  return rankedEntries(objects.map(entry=>({entry})),query).map(result=>result.entry);
}
type SearchEntry = ObjectEntry | CaveEntry;
export type CatalogSearchResult = (
  {kind:'object';entry:ObjectEntry} | {kind:'cave';entry:CaveEntry}
) & {planCount:number;modelCount:number};

function relevance(entry:SearchEntry, query:string, words:string[]):number {
  const id=normalize(entry.id),name=normalize(entry.name);
  if(id===query)return 6;
  if(name===query)return 5;
  if(name.startsWith(query))return 4;
  if(name.includes(query))return 3;
  if(words.every(word=>name.includes(word)))return 2;
  const metadata=normalize(`${entry.id} ${entry.name} ${entry.searchText}`);
  return words.every(word=>metadata.includes(word))?1:0;
}
function rankedEntries<T extends {entry:SearchEntry}>(entries:T[],query:string):T[] {
  const normalized=normalize(query),words=normalized.split(/\s+/).filter(Boolean);
  if(!words.length)return [];
  return entries.map(result=>({result,score:relevance(result.entry,normalized,words)}))
    .filter(result=>result.score>0)
    .sort((a,b)=>b.score-a.score || a.result.entry.name.localeCompare(b.result.entry.name,'pl') || a.result.entry.id.localeCompare(b.result.entry.id,'pl'))
    .map(({result})=>result);
}

export function searchCatalogEntries(catalog:Catalog,query:string):CatalogSearchResult[] {
  const objects=new Map(catalog.objects.map(object=>[object.id,object]));
  const planIds=new Set(catalog.plans.map(plan=>plan.id)),modelIds=new Set(catalog.models.map(model=>model.id));
  const materials=(entries:ObjectEntry[])=>({
    planCount:new Set(entries.flatMap(entry=>entry.planIds).filter(id=>planIds.has(id))).size,
    modelCount:new Set(entries.flatMap(entry=>entry.modelIds).filter(id=>modelIds.has(id))).size,
  });
  return rankedEntries<CatalogSearchResult>([
    ...catalog.objects.map(entry=>({kind:'object' as const,entry,...materials([entry])})),
    // sourceCaveId belongs to the plan source namespace, not the GPS C-xxxx namespace.
    // Only the cave's explicit object IDs connect it to these materials.
    ...catalog.caves.map(entry=>({kind:'cave' as const,entry,...materials(entry.objectIds.map(id=>objects.get(id)).filter((object):object is ObjectEntry=>!!object))})),
  ],query);
}
export function intersects(a: Extent, b: Extent): boolean {return a[0] <= b[2] && a[2] >= b[0] && a[1] <= b[3] && a[3] >= b[1];}
export function eligiblePlans(plans: PlanEntry[], extent: Extent, resolution: number, selected: Set<string>, hidden: Set<string>): PlanEntry[] {
  return plans.filter(p => !hidden.has(p.id) && intersects(p.extent,extent) && (selected.has(p.id) || (resolution <= 1 && Math.max(p.extent[2]-p.extent[0],p.extent[3]-p.extent[1])/resolution >= 64)));
}
export function formatCoordinate(c: Coordinate): string {
  const f = new Intl.NumberFormat('pl-PL',{maximumFractionDigits:1});
  return `X — północ: ${f.format(c[1])} m · Y — wschód: ${f.format(c[0])} m`;
}
export function escapeHtml(value: unknown): string {return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));}
export async function readJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url,{signal});
  if (!response.ok) throw new Error(`Nie udało się wczytać danych (HTTP ${response.status}).`);
  return response.json();
}
