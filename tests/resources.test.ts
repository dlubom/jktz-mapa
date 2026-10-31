import {test} from 'node:test';
import assert from 'node:assert/strict';
import {ImagePool} from '../src/resources.ts';

test('image pool bounds concurrency, aborts obsolete fetches and disposes decoded images', async () => {
  let active=0, max=0, closed=0;
  const pool = new ImagePool(2,16,async (_url, signal) => {
    active++; max=Math.max(max,active);
    await new Promise<void>((resolve,reject)=>{const t=setTimeout(resolve,10); signal.addEventListener('abort',()=>{clearTimeout(t);reject(new DOMException('aborted','AbortError'));},{once:true});}).finally(()=>active--);
    return {width:2,height:2,close(){closed++;}} as ImageBitmap;
  },()=>{});
  pool.want(['a','b','c']);
  await new Promise(r=>setTimeout(r,3));
  pool.want(['d']);
  await new Promise(r=>setTimeout(r,40));
  assert.ok(max<=2); assert.ok(pool.get('d')); assert.equal(pool.get('a'),undefined);
  pool.dispose(); assert.ok(closed>=1); assert.equal(pool.bytes,0);
});

test('retry recovers an unavailable image and clearing releases the cache', async () => {
  let attempts=0,closed=0;
  const pool=new ImagePool(1,64,async()=>{if(++attempts===1)throw new Error('offline');return {width:2,height:2,close(){closed++;}} as ImageBitmap;},()=>{});
  pool.want(['plan']);await new Promise(r=>setTimeout(r,5));assert.equal(pool.stats.failed,1);
  pool.retry();await new Promise(r=>setTimeout(r,5));assert.ok(pool.get('plan'));assert.equal(pool.stats.failed,0);
  pool.clear();assert.equal(pool.bytes,0);assert.equal(closed,1);pool.dispose();
});
test('decoded cache stays within its byte budget while navigating', async () => {
  let closed=0;const pool=new ImagePool(1,16,async()=>({width:2,height:2,close(){closed++;}} as ImageBitmap),()=>{});
  for(const id of ['a','b','c']){pool.want([id]);await new Promise(r=>setTimeout(r,5));assert.ok(pool.get(id));assert.ok(pool.bytes<=16);}
  assert.equal(closed,2);pool.dispose();
});
