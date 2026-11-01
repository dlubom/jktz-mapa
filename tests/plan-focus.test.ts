import {test} from 'node:test';
import assert from 'node:assert/strict';
import {Plans} from '../src/plans.ts';
import type {Extent, PlanEntry} from '../src/types.ts';

const extent:Extent=[0,0,200,200];
const entries:PlanEntry[]=['a','b','c'].map(id=>({
  id,name:id,extent:[...extent],nativeResolution:.1,objectIds:[],
  preview:{url:`${id}-preview.webp`,width:200,height:200},
  levels:[{level:0,resolution:.1,width:2000,height:2000,columns:4,rows:4}],
  tileSize:512,tileUrl:`${id}-{level}-{x}-{y}.webp`,detailUrl:`${id}.json`,
}));

// Only the canvas and map boundary need doubles in Node. The constructor,
// OpenLayers source/layer, focus transitions and draw selection stay real.
function setup(padding?:()=>number[]){
  const context={globalAlpha:1,drawImage(){}};
  const canvas={width:0,height:0,getContext:()=>context};
  const previous=Object.getOwnPropertyDescriptor(globalThis,'document');
  Object.defineProperty(globalThis,'document',{configurable:true,value:{createElement:(tag:string)=>{
    assert.equal(tag,'canvas');return canvas;
  }}});
  const fits:{extent:Extent;options:{padding:number[];duration:number;maxZoom:number}}[]=[];
  const events:string[]=[];
  let resolution=1;
  const view={
    cancelAnimations:()=>events.push('cancel'),
    fit:(fitExtent:Extent,options:{padding:number[];duration:number;maxZoom:number})=>{
      events.push('fit');fits.push({extent:fitExtent,options});resolution=2;
    },
    getResolution:()=>resolution,
  };
  let plans:Plans;
  try{
    plans=new Plans({addLayer(){},getView:()=>view} as never,entries,()=>events.push('report'),padding);
  }finally{
    if(previous)Object.defineProperty(globalThis,'document',previous);
    else Reflect.deleteProperty(globalThis,'document');
  }
  let wanted:string[]=[];
  plans.pool.want=urls=>{wanted=urls;};
  const render=(scale=1)=>{
    (plans as unknown as {render:(extent:Extent,resolution:number,pixelRatio:number,size:number[])=>unknown}).render(extent,scale,1,[200,200]);
    return [...plans.active];
  };
  return {plans,render,fits,events,wanted:()=>wanted};
}

function settings(plans:Plans){
  return {
    hidden:[...plans.hidden],selected:[...plans.selected],order:[...plans.order],
    opacity:[...plans.opacity],enabled:plans.enabled,visible:plans.layer.getVisible(),
  };
}

test('closing plan isolation restores the rendered plans and preserves manual settings',()=>{
  const {plans,render}=setup();
  plans.toggle('a',true);plans.toggle('b',true);plans.toggle('c',false);
  plans.move('b',-1);plans.opacity.set('a',.4);plans.opacity.set('b',.9);
  plans.show(entries[0]);
  const before=settings(plans);
  assert.deepEqual(render(),['b','a']);
  plans.setIsolation(true);
  assert.equal(plans.focusId,'a');assert.equal(plans.isolated,true);
  assert.deepEqual(render(),['a']);
  assert.deepEqual(settings(plans),before);
  plans.endFocus();
  assert.equal(plans.focusId,null);assert.equal(plans.isolated,false);
  assert.deepEqual(render(),['b','a']);
  assert.deepEqual(settings(plans),before);
  plans.dispose();
});

test('choosing a new plan moves isolation to that plan and retains whole-preview loading',()=>{
  const {plans,render,wanted}=setup();
  plans.show(entries[0]);plans.setIsolation(true);plans.show(entries[1]);
  assert.equal(plans.focusId,'b');assert.equal(plans.isolated,true);
  assert.deepEqual(plans.order,['c','a','b']);
  assert.deepEqual(render(2),['b']);
  assert.deepEqual(wanted(),['b-preview.webp']);
  plans.dispose();
});

test('hiding the focused plan closes focus and isolation but preserves other selections',()=>{
  const {plans,render}=setup();
  plans.toggle('a',true);plans.show(entries[1]);plans.setIsolation(true);
  plans.toggle('b',false);
  assert.equal(plans.focusId,null);assert.equal(plans.isolated,false);
  assert.deepEqual([...plans.selected],['a']);assert.deepEqual([...plans.hidden],['b']);
  assert.deepEqual(render(2),['a']);
  plans.dispose();
});

test('isolation and closing focus leave globally disabled plans disabled',()=>{
  const {plans,render}=setup();
  plans.show(entries[0]);plans.enabled=false;plans.layer.setVisible(false);
  const before=settings(plans);
  plans.setIsolation(true);assert.deepEqual(settings(plans),before);
  assert.deepEqual(render(),[]);
  plans.endFocus();assert.deepEqual(settings(plans),before);
  plans.dispose();
});

test('show reports focus before fitting and fit uses current toolbar padding without changing focus',()=>{
  let toolbar=false;
  const {plans,events,fits,render,wanted}=setup(()=>toolbar?[35,35,100,35]:[35,35,35,35]);
  // The report in show makes the toolbar visible before padding is measured.
  (plans as unknown as {report:()=>void}).report=()=>{events.push('report');toolbar=plans.focusId!==null;};
  plans.show(entries[0]);
  assert.deepEqual(events.slice(0,3),['report','cancel','fit'],'whole-plan fit cancels a still-running object-selection animation');
  assert.deepEqual(fits[0],{extent,options:{padding:[35,35,100,35],duration:0,maxZoom:24}});
  plans.setIsolation(true);const before=settings(plans);
  plans.fit(entries[0]);
  assert.equal(plans.focusId,'a');assert.equal(plans.isolated,true);
  assert.deepEqual(settings(plans),before);
  assert.deepEqual(render(2),['a']);assert.deepEqual(wanted(),['a-preview.webp']);
  assert.equal(fits.length,2);
  plans.dispose();
});

test('fit alone preserves focus and order and uses the preview footprint',()=>{
  const {plans,fits}=setup();
  const plan={...entries[0],preview:{...entries[0].preview,extent:[10,20,190,180] as Extent}};
  const before=settings(plans);
  plans.fit(plan);
  assert.equal(plans.focusId,null);assert.equal(plans.isolated,false);
  assert.deepEqual(settings(plans),before);
  assert.deepEqual(fits[0],{extent:[10,20,190,180],options:{padding:[35,35,35,35],duration:0,maxZoom:24}});
  plans.dispose();
});

test('render reports changed visible plans without waiting for an image fetch',async()=>{
  const {plans,render}=setup();
  const states:{active:string[];reduced:boolean}[]=[];
  (plans as unknown as {report:()=>void}).report=()=>states.push({active:[...plans.active],reduced:plans.reduced});
  plans.show(entries[0]);states.length=0;
  render(2);
  await Promise.resolve();
  assert.deepEqual(states,[{active:['a'],reduced:false}]);
  render(2);
  await Promise.resolve();
  assert.equal(states.length,1,'an unchanged render does not create a report loop');
  plans.enabled=false;render(2);
  await Promise.resolve();
  assert.deepEqual(states[1],{active:[],reduced:false});
  plans.dispose();
});

test('a report queued by render is ignored after the plan layer is disposed',async()=>{
  const {plans,render}=setup();
  let reports=0;
  plans.show(entries[0]);
  (plans as unknown as {report:()=>void}).report=()=>reports++;
  render(2);plans.dispose();
  await Promise.resolve();
  assert.equal(reports,0);
});

test('render reports memory reduction changes with the same active plan list',async()=>{
  const {plans,render}=setup();
  const states:{active:string[];reduced:boolean}[]=[];
  (plans as unknown as {report:()=>void}).report=()=>states.push({active:[...plans.active],reduced:plans.reduced});
  render(.1);await Promise.resolve();
  render(1);await Promise.resolve();
  assert.deepEqual(states,[
    {active:['a','b','c'],reduced:true},
    {active:['a','b','c'],reduced:false},
  ]);
  plans.dispose();
});
