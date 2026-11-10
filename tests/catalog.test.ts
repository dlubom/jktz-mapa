import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {once} from 'node:events';
import {normalize, searchCatalog, eligiblePlans, formatCoordinate, readJson} from '../src/catalog.ts';

test('search finds Polish names and identifiers without diacritics', () => {
  const objects = [{id:'T.A-01',name:'Żółta Jaskinia',searchText:'Żółta Jaskinia 001197'}];
  assert.equal(normalize(' ŁÓDŹ '), 'lodz');
  assert.equal(searchCatalog(objects as never, 'zolta')[0].id, 'T.A-01');
  assert.equal(searchCatalog(objects as never, '001197')[0].id, 'T.A-01');
  assert.equal(searchCatalog(objects as never, 'brak').length, 0);
});
test('whole-plan exception applies only to chosen visible plan, no arbitrary catalog cap', () => {
  const plans = Array.from({length:30},(_,i)=>({id:String(i),extent:[0,0,200,200]}));
  assert.equal(eligiblePlans(plans as never,[0,0,500,500],2,new Set(['1']),new Set()).length,1);
  assert.equal(eligiblePlans(plans as never,[0,0,500,500],1,new Set(),new Set()).length,30);
  assert.equal(eligiblePlans(plans as never,[300,300,500,500],1,new Set(['1']),new Set()).length,0);
  assert.equal(eligiblePlans(plans as never,[0,0,500,500],1,new Set(),new Set(['1'])).length,29);
});
test('display labels use northing as X, easting as Y', () => {
  assert.match(formatCoordinate([571469,156352]), /X.*156\s?352.*Y.*571\s?469/);
});
test('name matches rank above incidental mentions in source notes',()=>{
  const objects=[{id:'a',name:'Awen',searchText:'uwaga: Miętusia'},{id:'b',name:'Piwnica Miętusia',searchText:''}];
  assert.equal(searchCatalog(objects as never,'mietusia')[0].id,'b');
});

test('catalog requests can ask the HTTP cache to revalidate', async () => {
  const server = createServer((request, response) => {
    const revalidate = request.headers['cache-control'] === 'max-age=0';
    response.end(JSON.stringify({release: revalidate ? 'current' : 'cached'}));
  });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  try {
    const address = server.address();
    assert.ok(address && typeof address !== 'string');
    const catalog = await readJson(`http://127.0.0.1:${address.port}/data/catalog.json`, undefined, 'no-cache');
    assert.deepEqual(catalog, {release: 'current'});
  } finally {
    server.close();
  }
});
