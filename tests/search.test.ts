import {test} from 'node:test';
import assert from 'node:assert/strict';
import * as catalogModule from '../src/catalog.ts';
import type {Catalog, CaveEntry, ObjectEntry, PlanEntry, ModelEntry} from '../src/types.ts';

type SearchResult={kind:'object'|'cave';entry:ObjectEntry|CaveEntry;planCount:number;modelCount:number};
function search(catalog:Catalog,query:string):SearchResult[]{
  const fn=(catalogModule as unknown as {searchCatalogEntries?:(catalog:Catalog,query:string)=>SearchResult[]}).searchCatalogEntries;
  assert.equal(typeof fn,'function','catalog search must rank cave and object entries together');
  return fn!(catalog,query);
}
function object(id:string,name:string,other:Partial<ObjectEntry>={}):ObjectEntry{
  return {id,name,searchText:'',coordinate:null,detailUrl:'',best:{id:'best'},planIds:[],modelIds:[],...other};
}
function cave(id:string,name:string,other:Partial<CaveEntry>={}):CaveEntry{
  return {id,name,searchText:'',objectIds:[],detailUrl:'',...other};
}
function catalog(objects:ObjectEntry[]=[],caves:CaveEntry[]=[],plans:PlanEntry[]=[],models:ModelEntry[]=[]):Catalog{
  return {schemaVersion:1,crs:'EPSG:2180',generatedAt:'',sources:[],counts:{},extent:[0,0,1,1],objects,caves,plans,models};
}

test('one relevance order ranks both types by exact id, exact name, prefix, substring and metadata',()=>{
  const entries=catalog([
    object('notes','Awen',{searchText:'Przy Miętusiej, Miętusia'}),
    object('prefix','Miętusia Niżnia'),
    object('Miętusia','Zbiornik'),
  ],[
    cave('substring','Piwnica Miętusia'),
    cave('name','Miętusia'),
  ]);
  assert.deepEqual(search(entries,'mietusia').map(result=>result.entry.id),['Miętusia','name','prefix','substring','notes']);
  assert.deepEqual(search(entries,'MIĘTUSIA').map(result=>result.entry.id),['Miętusia','name','prefix','substring','notes']);
});

test('all words in a name outrank matches distributed through metadata',()=>{
  const entries=catalog([
    object('notes','Awen',{searchText:'jama; archiwum mała'}),
    object('words','Mała Długa Jama'),
  ],[
    cave('substring','Dolna Mała Jama'),
    cave('prefix','Mała Jama Nad Progiem'),
    cave('name','Mała Jama'),
  ]);
  assert.deepEqual(search(entries,'mala jama').map(result=>result.entry.id),['name','prefix','substring','words','notes']);
});

test('exact cave ids outrank incidental object mentions and normalized identifiers retain priority',()=>{
  const entries=catalog([
    object('object','Awen',{searchText:'C-ŁÓDŹ'}),
    object('C-ŁÓDŹ-extra','Zimna'),
  ],[cave('C-ŁÓDŹ','Żółta Jama')]);
  assert.equal(search(entries,'c-lodz')[0].entry.id,'C-ŁÓDŹ');
  assert.equal(search(entries,'c-lodz')[0].kind,'cave');
});

test('a common query returns all ranked entries with no separate type limits',()=>{
  const objects=Array.from({length:55},(_,i)=>object(`O-${i}`,`Jama ${String(i).padStart(3,'0')}`));
  const caves=Array.from({length:45},(_,i)=>cave(`C-${i}`,`Jama ${String(i+55).padStart(3,'0')}`));
  const results=search(catalog(objects,caves),'jama');
  assert.equal(results.length,100);
  assert.equal(results.filter(result=>result.kind==='object').length,55);
  assert.equal(results.filter(result=>result.kind==='cave').length,45);
  assert.deepEqual(search(catalog(objects,caves),'   '),[]);
  assert.deepEqual(search(catalog(objects,caves),'nieistniejąca'),[]);
});

test('availability follows explicit object ids and deduplicates shared cave materials',()=>{
  const entries=catalog([
    object('O-1','Jama pierwszy',{planIds:['p','p','missing-plan'],modelIds:['m']}),
    object('O-2','Jama drugi',{planIds:['p','q'],modelIds:['m','missing-model']}),
    object('O-3','Jama podobna',{planIds:['wrong'],modelIds:['wrong-model']}),
  ],[
    cave('C-1','Jama',{objectIds:['O-1','O-2','missing-object']}),
    cave('C-2','Jama',{objectIds:[]}),
  ],[
    {id:'p',name:'Plan'} as PlanEntry,
    {id:'q',name:'Plan drugi'} as PlanEntry,
    {id:'wrong',name:'Jama',sourceCaveId:'C-2'} as PlanEntry,
  ],[
    {id:'m',name:'Ciąg'} as ModelEntry,
    {id:'wrong-model',name:'Jama'} as ModelEntry,
  ]);
  const results=search(entries,'jama');
  const availability=(id:string)=>{const result=results.find(result=>result.entry.id===id)!;return [result.planCount,result.modelCount];};
  assert.deepEqual(availability('O-1'),[1,1]);
  assert.deepEqual(availability('O-2'),[2,1]);
  assert.deepEqual(availability('C-1'),[2,1]);
  assert.deepEqual(availability('C-2'),[0,0],'same names and source ids from a different namespace do not imply GPS relationships');
});
