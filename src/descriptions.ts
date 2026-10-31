import type {SourceRecord} from './types.ts';
import {escapeHtml as e} from './catalog.ts';
import dictionaryData from './data/cave-descriptions.json' with {type:'json'};

export interface DescriptionEdition {
  url:string; title:string; source:string; scope:string; author?:string; version?:string;
}
export interface DescriptionDictionary {
  editions:Record<string,DescriptionEdition>;
  caves:Record<string,{primary:string;otherEditions?:string[]}>;
}
export interface Descriptions {primary?:DescriptionEdition;otherEditions:DescriptionEdition[]}
const dictionary:DescriptionDictionary=dictionaryData;

function webUrl(value:unknown):string|undefined {
  if(typeof value!=='string')return;
  try{const url=new URL(value);return ['http:','https:'].includes(url.protocol)?url.href:undefined;}catch{return;}
}

/** Only explicit GPS cave IDs and their original cave references select a description. */
export function resolveDescriptions(caveId:string|undefined,refs:SourceRecord[],data:DescriptionDictionary=dictionary):Descriptions {
  if(!caveId)return {otherEditions:[]};
  const assignment=data.caves[caveId];
  const edition=(id:string)=>{const entry=data.editions[id],url=webUrl(entry?.url);return entry&&url?{...entry,url}:undefined;};
  const pig=refs.find(ref=>ref.cave_id===caveId&&ref.scope==='cave'&&ref.system==='PIG'&&webUrl(ref.url));
  const primary=(assignment&&edition(assignment.primary))||(pig?{
    url:webUrl(pig.url)!,title:`Karta PIG ${pig.external_id}`,source:'PIG',scope:'jaskinia'
  }:undefined);
  const seen=new Set(assignment?[assignment.primary]:[]),otherEditions:DescriptionEdition[]=[];
  for(const id of assignment?.otherEditions||[]){
    const entry=edition(id);
    if(entry&&!seen.has(id)){seen.add(id);otherEditions.push(entry);}
  }
  return {primary,otherEditions};
}

const externalLink=(url:string,label:string)=>`<a href="${e(url)}" target="_blank" rel="noopener noreferrer">${e(label)} ↗</a>`;
const editionMetadata=(entry:DescriptionEdition)=>`<p class="muted">Źródło: ${e(entry.source)}${entry.author?` · ${e(entry.author)}`:''}<br>Zakres: ${e(entry.scope)}${entry.version?` · Stan opracowania: ${e(entry.version)}`:''}</p>`;

export function renderDescription({primary}:Descriptions):string {
  return primary?`<div class="cave-description">${externalLink(primary.url,'Opis jaskini')}<p class="description-title">${e(primary.title)}</p>${editionMetadata(primary)}</div>`:'';
}

/** Deduplicate normal links; callers retain all original rows in the raw metadata. */
export function renderDescriptionSources({primary,otherEditions}:Descriptions,refs:SourceRecord[]):string {
  const seen=new Set(primary?[primary.url]:[]),rows:string[]=[];
  for(const entry of otherEditions){
    const title=seen.has(entry.url)?`${e(entry.title)} <span class="muted">· ${entry.url===primary?.url?'odnośnik przy nazwie':'wspólny odnośnik powyżej'}</span>`:externalLink(entry.url,entry.title);
    seen.add(entry.url);rows.push(`<div>${title}${editionMetadata(entry)}</div>`);
  }
  let primaryReferenced=false;
  for(const ref of refs){
    const url=webUrl(ref.url),label=`${ref.system}: ${ref.external_id}`;
    if(url&&seen.has(url)){
      if(url===primary?.url&&!primaryReferenced){rows.push(`<p>${e(label)} <span class="muted">· odnośnik przy nazwie</span></p>`);primaryReferenced=true;}
      continue;
    }
    if(url)seen.add(url);
    rows.push(`<p>${url?externalLink(url,label):e(label)}</p>`);
  }
  return `<div class="description-sources">${rows.join('')||'<p class="muted">Brak dodatkowych odnośników.</p>'}</div>`;
}
