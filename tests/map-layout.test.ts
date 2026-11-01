import {test} from 'node:test';
import assert from 'node:assert/strict';
import {planFitPadding} from '../src/map-layout.ts';

test('whole-plan fit reserves the entire toolbar even on a short map',()=>{
  // 393 x 400 screen: map starts at 64, toolbar ends at 290.
  // The former height-100 cap left the top of the drawing under the toolbar.
  assert.deepEqual(planFitPadding(64,290),[241,35,35,35]);
  assert.deepEqual(planFitPadding(64,254),[205,35,35,35]);
});

test('whole-plan fit uses ordinary margins when the toolbar is hidden',()=>{
  assert.deepEqual(planFitPadding(78,null),[35,35,35,35]);
});
