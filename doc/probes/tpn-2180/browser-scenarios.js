// Playwright CLI run-code --filename browser-scenarios.js
async (page) => {
  const context=await page.context().browser().newContext({viewport:{width:1000,height:760}});
  const p=await context.newPage();
  const requests=[],errors=[],rows=[];
  p.on('request',r=>{if(r.url().includes('tpn.obliview.com'))requests.push(r.url());});
  p.on('pageerror',e=>errors.push(e.message));
  async function settle(){await p.waitForFunction(()=>{const s=window.probe.snapshot();return s.started>0&&s.started===s.loaded+s.failed;},{},{timeout:15000});await p.waitForFunction(()=>window.probe.snapshot().renderComplete>0,{},{timeout:15000});}
  async function capture(name){await settle();rows.push({name,snapshot:await p.evaluate(()=>window.probe.snapshot()),message:await p.locator('#status').textContent()});await p.screenshot({path:`/private/tmp/jktz-tpn-evidence/${name}.png`});}
  await p.goto('http://127.0.0.1:8765/?dataset=NMT');
  await settle();
  await p.locator('#osm').check();
  await p.locator('#gap').click();
  await p.evaluate(()=>window.probe.setSource('NMT'));
  await capture('natural-gap-NMT');
  await p.locator('#known').click();
  await p.evaluate(()=>window.probe.setSource('NMT'));
  await settle();
  await context.route('https://tpn.obliview.com/**',route=>route.abort('internetdisconnected'));
  await p.locator('#retry').click();
  await capture('injected-tpn-outage');
  await context.unroute('https://tpn.obliview.com/**');
  await p.locator('#retry').click();
  await capture('manual-recovery');
  const oneTile='https://tpn.obliview.com/Data/rgb_2020/17/72811/44862.jpg';
  await context.route(oneTile,route=>route.abort('internetdisconnected'));
  await p.evaluate(()=>window.probe.setSource('rgb_2020'));
  await capture('single-missing-tile');
  await context.unroute(oneTile);
  await p.locator('#osm').uncheck();
  for (const resolution of [4,0.07]){
    const first=requests.length;
    await p.evaluate(res=>{window.probe.map.getView().setResolution(res);window.probe.setSource('rgb_2020');},resolution);
    await capture(`resolution-${resolution}`);
    rows.at(-1).sourceZooms=[...new Set(requests.slice(first).map(url=>Number(url.split('/').at(-3))))];
  }
  await p.evaluate(()=>{window.probe.map.getView().setResolution(1);window.probe.map.getView().setRotation(Math.PI/9);window.probe.tpn.setOpacity(.5);window.probe.setSource('rgb_2020');});
  await capture('rotation20-opacity50');
  await context.close();
  return {date:new Date().toISOString(),rows,errors};
}
