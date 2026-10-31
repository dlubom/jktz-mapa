import type {ObjectEntry, PlanEntry, Extent, Coordinate} from './types.ts';
export function normalize(value: string): string {
  return value.toLocaleLowerCase('pl').replaceAll('ł', 'l').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim();
}
export function searchCatalog(objects: ObjectEntry[], query: string): ObjectEntry[] {
  const words = normalize(query).split(/\s+/).filter(Boolean);
  if (!words.length) return [];
  const score=(o:ObjectEntry)=>normalize(o.id)===normalize(query)?5:normalize(o.name).startsWith(normalize(query))?4:normalize(o.name).includes(normalize(query))?3:words.every(w=>normalize(o.name).includes(w))?2:0;
  return objects.filter(o => words.every(w => normalize(`${o.name} ${o.id} ${o.searchText}`).includes(w)))
    .sort((a,b) => score(b)-score(a) || a.name.localeCompare(b.name,'pl'));
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
