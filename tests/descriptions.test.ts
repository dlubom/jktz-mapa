import {test} from 'node:test';
import assert from 'node:assert/strict';
import {resolveDescriptions, renderDescription, renderDescriptionSources} from '../src/descriptions.ts';
import type {DescriptionDictionary} from '../src/descriptions.ts';

const pigUrl='https://jaskiniepolski.pgi.gov.pl/Details/Information/1473';
const pigRefs=[
  {cave_id:'C-0167',system:'PIG',scope:'cave',ref_type:'catalog_id',external_id:'1473',url:pigUrl,notes:'Original catalog record'},
  {cave_id:'C-0167',system:'PIG',scope:'cave',ref_type:'url',external_id:pigUrl,url:pigUrl}
];
const url='https://antkiewiczjaskinie.pl/system-ptasia-studnia-t-e-11-06t-e-11-10t-e-11-09/';

test('explicit overrides win over PIG for all three caves, excluding the lower entrance',()=>{
  for(const id of ['C-0167','C-0273','C-0072']){
    const refs=pigRefs.map(ref=>({...ref,cave_id:id}));
    const selected=resolveDescriptions(id,refs);
    assert.equal(selected.primary?.url,url);
    assert.equal(selected.primary?.title,'System Ptasia Studnia');
    assert.equal(selected.primary?.author,'Anna Antkiewicz');
    assert.equal(selected.primary?.scope,'system jaskiniowy');
    assert.equal(selected.primary?.version,'1999/2004');
  }
  assert.equal(resolveDescriptions('C-0997',[]).primary,undefined);
  assert.equal(resolveDescriptions('MTZ-0066',[]).primary,undefined);
});

test('fallback uses only a confirmed PIG URL assigned to this cave',()=>{
  const selected=resolveDescriptions('C-0346',pigRefs.map(ref=>({...ref,cave_id:'C-0346'})));
  assert.equal(selected.primary?.url,pigUrl);
  assert.equal(selected.primary?.source,'PIG');
  assert.equal(selected.primary?.scope,'jaskinia');
  assert.equal(selected.primary?.version,undefined);
  assert.equal(resolveDescriptions('C-0346',pigRefs).primary,undefined);
  assert.equal(resolveDescriptions(undefined,pigRefs).primary,undefined);
  for(const refs of [[],[{system:'PIG',cave_id:'C-0346',scope:'cave',external_id:'1473'}],[{...pigRefs[0],cave_id:'C-0346',scope:'object'}],[{...pigRefs[0],cave_id:'C-0346',system:'TPN'}]]){
    assert.equal(renderDescription(resolveDescriptions('C-0346',refs)),'');
  }
});

test('data alone can change the primary edition and retain other versions in sources',()=>{
  const dictionary:DescriptionDictionary={
    editions:{
      old:{url:'https://example.org/old',title:'Older system',source:'Publisher',scope:'system jaskiniowy',version:'1999'},
      newer:{url:'https://example.org/new',title:'Newer system',source:'Publisher',scope:'system jaskiniowy',version:'2004'}
    },
    caves:{'C-0167':{primary:'newer',otherEditions:['old','newer','old']}}
  };
  let selected=resolveDescriptions('C-0167',pigRefs,dictionary);
  assert.equal(selected.primary?.url,'https://example.org/new');
  assert.deepEqual(selected.otherEditions.map(d=>d.version),['1999']);
  let sources=renderDescriptionSources(selected,pigRefs);
  assert.match(sources,/href="https:\/\/example.org\/old"/);
  assert.match(sources,/1999/);
  assert.equal((sources.match(/href=/g)||[]).length,2,'one older version and one original PIG address');
  dictionary.caves['C-0167']={primary:'old',otherEditions:['newer']};
  selected=resolveDescriptions('C-0167',pigRefs,dictionary);
  assert.equal(selected.primary?.version,'1999');
  sources=renderDescriptionSources(selected,pigRefs);
  assert.match(sources,/href="https:\/\/example.org\/new"/);
});

test('visible URLs are deduplicated across the primary, versions and original references',()=>{
  const original=structuredClone(pigRefs);
  for(const selected of [resolveDescriptions('C-0167',pigRefs),resolveDescriptions('C-0167',pigRefs,{editions:{},caves:{}})]){
    const html=renderDescription(selected)+renderDescriptionSources(selected,[...pigRefs,...pigRefs,{system:'NR_INWENT',external_id:'T.E-11.06',url:null}]);
    assert.equal((html.match(new RegExp(`href="${pigUrl}"`,'g'))||[]).length,1);
    assert.match(html,/1473/);
    assert.match(html,/T.E-11.06/);
  }
  assert.deepEqual(pigRefs,original,'source metadata remain unchanged');
});

test('editions sharing a URL keep their version metadata without repeating the address',()=>{
  const dictionary:DescriptionDictionary={
    editions:{
      old:{url:'https://example.org/system',title:'Older system',source:'Publisher',scope:'system jaskiniowy',version:'1999'},
      newer:{url:'https://example.org/system',title:'Newer system',source:'Publisher',scope:'system jaskiniowy',version:'2004'}
    },
    caves:{'C-0167':{primary:'newer',otherEditions:['old','old','newer']}}
  };
  const selected=resolveDescriptions('C-0167',[],dictionary);
  assert.deepEqual(selected.otherEditions.map(entry=>entry.version),['1999']);
  const sources=renderDescriptionSources(selected,[]);
  assert.match(sources,/1999/);
  assert.equal(((renderDescription(selected)+sources).match(/href=/g)||[]).length,1);
});

test('external links open a new tab, escape metadata and reject non-web URLs',()=>{
  const dictionary:DescriptionDictionary={editions:{entry:{url:'https://example.org/?x=1&y=2',title:'<script>',source:'A & B',scope:'jaskinia',version:'2004'}},caves:{'C-1':{primary:'entry'}}};
  const html=renderDescription(resolveDescriptions('C-1',[],dictionary));
  assert.match(html,/Opis jaskini ↗/);
  assert.match(html,/target="_blank"/);
  assert.match(html,/rel="noopener noreferrer"/);
  assert.match(html,/&lt;script&gt;/);
  assert.match(html,/A &amp; B/);
  for(const invalid of ['javascript:alert(1)','data:text/html,test','',null]){
    assert.equal(resolveDescriptions('C-0346',[{...pigRefs[0],cave_id:'C-0346',url:invalid}]).primary,undefined);
    assert.doesNotMatch(renderDescriptionSources({otherEditions:[]},[{system:'PIG',external_id:'1473',url:invalid}]),/href=/);
  }
});
