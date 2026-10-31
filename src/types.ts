export type Extent = [number, number, number, number];
export type Coordinate = [number, number];
export interface ObjectEntry {
  id: string; name: string; caveId?: string; caveName?: string; systemName?: string;
  coordinate: Coordinate | null; searchText: string; detailUrl: string;
  best: {id: string; source?: string; verificationStatus?: string; horizontalAccuracy?: number};
  modelIds: string[]; planIds: string[];
}
export interface ModelEntry {id: string; name: string; extent: Extent; objectIds: string[]; url: string; featureCount: number}
export interface PlanEntry {
  id: string; name: string; extent: Extent; nativeResolution: number; objectIds: string[];
  sourceCaveId?: string | null; preview: {url: string; width: number; height: number; extent?: Extent};
  levels: {level: number; resolution: number; width: number; height: number; columns: number; rows: number}[];
  tileSize: number; tileUrl: string; detailUrl: string; orientationStatus?: string; gutter?: number;
}
export interface CaveEntry {id:string;name:string;systemName?:string|null;objectIds:string[];searchText:string;detailUrl:string}
export interface Catalog {
  schemaVersion: number; crs: string; generatedAt: string;
  sources: {key: string; repository: string; tag: string; commit: string; url: string; assets: unknown[]; licenses?:{name:string;url:string;text:string}[]}[];
  counts: Record<string, number>; extent: Extent; objects: ObjectEntry[]; caves:CaveEntry[]; models: ModelEntry[]; plans: PlanEntry[];
}
export type SourceRecord = Record<string, unknown>;
export interface Measurement extends SourceRecord {id: string; object_id: string; coordinate: Coordinate | null; role: 'best'|'other'|'rejected'; differenceM: number | null}
export interface ObjectDetail {object: SourceRecord; cave: SourceRecord | null; best: SourceRecord; measurements: Measurement[]; externalRefs: SourceRecord[]; caveExternalRefs: SourceRecord[]; relations: SourceRecord[]; attachments: SourceRecord[]; modelIds: string[]; planIds: string[]}
