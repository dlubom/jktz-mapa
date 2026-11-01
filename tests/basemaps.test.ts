import {test} from 'node:test';
import assert from 'node:assert/strict';
import {basemapStatus, BasemapFailures, type BasemapStatusInput, type BasemapTile} from '../src/basemaps.ts';

const view:[number,number,number,number]=[565000,150000,566000,151000];
const tile=(state:BasemapTile['state'],extent=view,zoom=4):BasemapTile=>({state,extent,zoom});
const status=(changes:Partial<BasemapStatusInput>={})=>basemapStatus({id:'rgb_2020',resolution:1,extent:view,opacity:1,zoom:4,tiles:[tile('loaded')],osmState:'loaded',...changes});

test('selected imagery is inactive at the exact max resolution and asks for zoom',()=>{
  const result=status({resolution:6});
  assert.equal(result.actual,'osm');assert.equal(result.reason,'scale');
  assert.match(result.message,/Wybrano:.*2020.*TPN/);assert.match(result.message,/Widoczne: OpenStreetMap.*przybliż/);
  assert.equal(result.warning,'');
});
test('OSM is the actual basemap when chosen or when imagery opacity is zero',()=>{
  assert.equal(status({id:'osm',tiles:[]}).actual,'osm');
  const hidden=status({opacity:0});
  assert.equal(hidden.actual,'osm');assert.equal(hidden.reason,'opacity');assert.match(hidden.message,/0%/);
});
test('geology outside its published extent has no service warning',()=>{
  const result=status({id:'smgt_a_zakryta',extent:[500000,100000,501000,101000],tiles:[tile('error')]});
  assert.equal(result.actual,'osm');assert.equal(result.reason,'coverage');assert.match(result.message,/poza zasięgiem/);assert.equal(result.warning,'');
});
test('a viewport crossing geology bounds explicitly includes OSM',()=>{
  const result=status({id:'smgt_b_odkryta',extent:[554000,150000,555000,151000],tiles:[tile('loaded',[554000,150000,555000,151000])]});
  assert.equal(result.actual,'mixed');assert.equal(result.reason,'partial-coverage');assert.match(result.message,/PIG-PIB.*OpenStreetMap/);
});
test('a newly selected viewport starts as loading until its current tiles arrive',()=>{
  const result=status({tiles:[]});
  assert.equal(result.actual,'loading');assert.match(result.message,/OpenStreetMap.*wczytywanie TPN/);assert.equal(result.warning,'');
});
test('old errors outside the current viewport or at another zoom do not poison it',()=>{
  const result=status({tiles:[tile('loaded'),tile('error',[500000,100000,501000,101000]),tile('error',view,3)]});
  assert.equal(result.actual,'selected');assert.equal(result.warning,'');
});
test('partial and complete failures describe only the currently available basemap',()=>{
  const partial=status({id:'smgt_a_zakryta',tiles:[tile('loaded'),tile('error')]});
  assert.equal(partial.actual,'mixed');assert.equal(partial.reason,'error');assert.match(partial.warning,/geologicznego PIG-PIB.*OSM/);
  const failed=status({tiles:[tile('error')]});
  assert.equal(failed.actual,'osm');assert.equal(failed.reason,'error');assert.match(failed.message,/Widoczne: OpenStreetMap/);
  assert.match(failed.warning,/brak pokrycia lub błąd pobierania/);
});
test('loaded reprojection tiles still report missing source tiles as partial availability',()=>{
  const result=status({tiles:[tile('loaded')],sourceFailures:[tile('error')]});
  assert.equal(result.actual,'mixed');assert.equal(result.reason,'error');
});
test('recovery clears warnings and current loading does not claim complete imagery',()=>{
  assert.equal(status({tiles:[tile('loaded')]}).warning,'');
  const loading=status({tiles:[tile('loaded'),tile('loading')]});
  assert.equal(loading.actual,'mixed');assert.equal(loading.reason,'loading');assert.match(loading.message,/wczytywanie/);
});
test('translucent imagery truthfully includes OSM in the actual background',()=>{
  const result=status({opacity:.45});
  assert.equal(result.actual,'mixed');assert.match(result.message,/TPN.*OpenStreetMap.*45%/);
});
test('fallback loading and failure never claim OpenStreetMap is already visible',()=>{
  const loading=status({resolution:6,osmState:'loading'});
  assert.equal(loading.actual,'loading');assert.match(loading.message,/brak gotowego podkładu.*OpenStreetMap.*wczytywanie/);
  const failed=status({id:'osm',osmState:'error'});
  assert.equal(failed.actual,'none');assert.match(failed.message,/brak podkładu.*OpenStreetMap.*niedostępne/);
});
test('zero opacity on selected OSM is intentional transparency rather than a tile error',()=>{
  const hidden=status({id:'osm',opacity:0});
  assert.equal(hidden.actual,'none');assert.equal(hidden.reason,'opacity');assert.match(hidden.message,/krycie.*0%/);assert.doesNotMatch(hidden.message,/niedostępne/);
});
test('loaded geology does not claim that its unavailable fallback is visible',()=>{
  const result=status({id:'smgt_a_zakryta',osmState:'error'});
  assert.match(result.message,/PIG-PIB; zapasowy OpenStreetMap: kafle niedostępne/);
});
test('source gaps remain known after leaving a viewport until their tile recovers',()=>{
  const failures=new BasemapFailures();
  failures.record('18/1/2',view,18);
  assert.equal(failures.current([500000,100000,501000,101000],4,new Set([18])).length,0);
  const returned=failures.current(view,4,new Set([18]));
  assert.equal(returned.length,1);assert.equal(status({sourceFailures:returned}).reason,'error');
  assert.equal(failures.current(view,5,new Set([19])).length,0,'previous zoom errors do not poison the next zoom');
  failures.recover('18/1/2');
  assert.equal(status({sourceFailures:failures.current(view,4,new Set([18]))}).reason,'selected');
});
