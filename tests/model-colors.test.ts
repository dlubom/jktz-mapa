import assert from 'node:assert/strict';
import test from 'node:test';

import {assignModelColors} from '../src/model-colors.ts';
import type {Extent} from '../src/types.ts';

test('nearby surveys have different colors regardless of catalogue order',()=>{
  const models = Array.from({length:8},(_,i)=>({
    id:`survey-${i}`,
    extent:[i*14,0,i*14+1,1] as Extent,
  }));
  const colors = assignModelColors(models);
  assert.equal(new Set(colors.values()).size,8);
  assert.deepEqual(assignModelColors([...models].reverse()),colors);
  assert.deepEqual(assignModelColors([]),new Map());
});

test('the 100 m neighbor threshold uses distance between extents',()=>{
  const first={id:'first',extent:[0,0,1,1] as Extent};
  for(const [x,neighbors] of [[61,true],[62,false]] as const){
    const second={id:'second',extent:[x,81,x+1,82] as Extent};
    const colors=assignModelColors([first,second]);
    assert.equal(colors.get(first.id)!==colors.get(second.id),neighbors);
  }
});
