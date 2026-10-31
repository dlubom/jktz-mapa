// Local-only rendering probe; no production cache/eviction behavior.
async (page)=>{
 const browser=page.context().browser(),rows=[];
 for(const id of ['001197','001459-pza-2024','001212','001140','010865']){
  for(const dpr of [1,3])for(const mode of ['preview','tiles']){
   const context=await browser.newContext({viewport:dpr===3?{width:393,height:852}:{width:1200,height:800},deviceScaleFactor:dpr});
   const p=await context.newPage(),errors=[];p.on('pageerror',e=>errors.push(e.message));
   const cdp=await context.newCDPSession(p);
   await cdp.send('Network.enable');
   await cdp.send('Network.setCacheDisabled',{cacheDisabled:true});
   await cdp.send('Network.emulateNetworkConditions',{offline:false,latency:80,downloadThroughput:1250000,uploadThroughput:1250000});
   const start=Date.now();
   await p.goto(`http://127.0.0.1:8766/raster.html?id=${id}&mode=${mode}&resolution=0.25`);
   let completed=true;await p.waitForFunction(()=>window.rasterProbe?.snapshot().renderComplete>0,{},{timeout:15000}).catch(()=>completed=false);
   const readyMs=Date.now()-start;
   const snapshot=await p.evaluate(()=>window.rasterProbe.snapshot());
   const file=`/private/tmp/jktz-tpn-evidence/raster-${id}-${mode}-dpr${dpr}.png`;
   await p.screenshot({path:file,scale:'device'});
   const success=completed&&snapshot.loaded>0&&snapshot.failed===0&&errors.length===0;
   rows.push({id,dpr,mode,completed,success,readyMs,snapshot,errors,screenshot:file});
   await context.close();
  }
 }
 return {date:new Date().toISOString(),browser:browser.version(),profile:'10 Mb/s, 80 ms, cold cache, desktop CPU',rows};
}
