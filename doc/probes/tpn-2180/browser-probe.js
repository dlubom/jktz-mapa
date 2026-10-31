// Playwright CLI run-code --filename browser-probe.js
// Runs against an already served static dist on localhost:8765.
async (page) => {
  const browser = page.context().browser();
  const rows = [];
  for (const spec of [
    ...['rgb_2020','rgb_2018','NMT','nmpt'].map(dataset=>({dataset,dpr:1,mode:'xyz'})),
    {dataset:'rgb_2020',dpr:3,mode:'xyz'},
    {dataset:'rgb_2020',dpr:1,mode:'xyz-cors'},
    {dataset:'rgb_2020',dpr:1,mode:'data'},
  ]) {
    const context = await browser.newContext({viewport:spec.dpr===3?{width:393,height:852}:{width:1200,height:860},deviceScaleFactor:spec.dpr});
    const p = await context.newPage();
    const errors=[], requests=[], responses=[];
    p.on('pageerror',e=>errors.push(e.message));
    p.on('request',r=>{if(r.url().includes('tpn.obliview.com')) requests.push({url:r.url(),resourceType:r.resourceType()});});
    p.on('response',r=>{if(r.url().includes('tpn.obliview.com')) responses.push({url:r.url(),status:r.status(),headers:r.headers()});});
    const started=Date.now();
    await p.goto(`http://127.0.0.1:8765/?dataset=${spec.dataset}&mode=${spec.mode}`);
    let settled=true;
    await p.waitForFunction(()=>window.probe && window.probe.snapshot().started>0 && window.probe.snapshot().loaded+window.probe.snapshot().failed===window.probe.snapshot().started,{},{timeout:15000}).catch(()=>settled=false);
    if(spec.mode==='xyz') await p.waitForFunction(()=>window.probe.snapshot().renderComplete>0,{},{timeout:15000}).catch(()=>settled=false);
    const readyMs=Date.now()-started;
    const snapshot=await p.evaluate(()=>window.probe.snapshot());
    // Deliberate negative capability probe, separate from render errors.
    const pixelRead=await p.evaluate(()=>{try{document.querySelector('.tpn-canvas canvas').getContext('2d').getImageData(0,0,1,1);return 'allowed';}catch(e){return e.name;}});
    const filename=`/private/tmp/jktz-tpn-evidence/${spec.dataset}-${spec.mode}-dpr${spec.dpr}.png`;
    await p.screenshot({path:filename,scale:'device'});
    rows.push({spec,settled,readyMs,snapshot,errors,pixelRead,requests,responses,screenshot:filename});
    await context.close();
  }
  return {browser:browser.version(),date:new Date().toISOString(),rows};
}
