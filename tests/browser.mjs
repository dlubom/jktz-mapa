import {createServer} from 'node:http';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {resolve,extname} from 'node:path';
import assert from 'node:assert/strict';
import {chromium,firefox,webkit} from 'playwright';

const root=resolve('dist'),prefix='/jktz-mapa/';
const types={'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.geojson':'application/geo+json','.webp':'image/webp'};
const server=createServer(async(req,res)=>{try{const path=decodeURIComponent(new URL(req.url,'http://localhost').pathname);if(!path.startsWith(prefix)){res.writeHead(404).end();return;}const file=resolve(root,path.slice(prefix.length)||'index.html');if(!file.startsWith(root+'/')){res.writeHead(403).end();return;}const data=await readFile(file);res.writeHead(200,{'Content-Type':types[extname(file)]||'application/octet-stream'});res.end(data);}catch{res.writeHead(404).end('Not found');}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const url=`http://127.0.0.1:${server.address().port}${prefix}`;
const catalog=JSON.parse(await readFile('dist/data/catalog.json','utf8'));
await mkdir('output/playwright',{recursive:true});
const results=[];
try{
 for(const name of (process.env.BROWSERS||'chromium').split(',')){
  console.log(`Launching ${name}`);
  const browser=await({chromium,firefox,webkit}[name]).launch({headless:true,timeout:30000});
  try{
   for(const mobile of [false,true]){
    const context=await browser.newContext({viewport:mobile?{width:393,height:852}:{width:1440,height:960},deviceScaleFactor:mobile?3:1,hasTouch:mobile});
    const page=await context.newPage(),errors=[],requests=[],network=new Map(),finishedURLs=new Set();
    const caseName=`${name}-${mobile?'mobile':'desktop'}`;
    page.on('pageerror',e=>errors.push(e.message));
    page.on('request',r=>{requests.push(r.url());network.set(r,{url:r.url(),status:null,finished:false,failure:null});});
    page.on('response',r=>{const row=network.get(r.request());if(row)row.status=r.status();});
    page.on('requestfailed',r=>{const row=network.get(r);if(row)row.failure=r.failure()?.errorText;});
    page.on('requestfinished',async r=>{const row=network.get(r);if(row)row.finished=true;const response=await r.response().catch(()=>null);if(response?.status()===200)finishedURLs.add(r.url());});
    // Resource Timing is bounded telemetry, not a download-completion signal.
    // Keep its buffer small to cover the mobile regression with many map assets.
    await page.addInitScript(()=>{performance.setResourceTimingBufferSize(200);window.resourceTimingBufferFullCount=0;performance.addEventListener('resourcetimingbufferfull',()=>window.resourceTimingBufferFullCount++);});
    const waitForDownload=async(predicate,label)=>{const deadline=Date.now()+30000;while(![...finishedURLs].some(predicate)){assert.ok(Date.now()<deadline,`Timed out waiting for successful completed download: ${label}`);await page.waitForTimeout(50);}};
    const timing=()=>page.evaluate(()=>({entries:performance.getEntriesByType('resource').length,bufferFullEvents:window.resourceTimingBufferFullCount}));
    try{
    // Controlled external outage pins fallback behaviour, independent of TPN uptime.
    await page.route('https://tpn.obliview.com/**',r=>r.abort());
    await page.route('https://*.tile.openstreetmap.org/**',r=>r.abort());
    console.log(`Checking ${name} ${mobile?'mobile':'desktop'}`);
    const started=Date.now();await page.goto(url);
    await page.getByRole('heading',{name:'Warstwy i podkład'}).waitFor();
    const readyMs=Date.now()-started;
    assert.equal(await page.locator('#layer-best').isChecked(),true);assert.equal(await page.locator('#layer-other').isChecked(),false);assert.equal(await page.locator('#layer-rejected').isChecked(),false);assert.equal(await page.locator('#layer-differences').isChecked(),false);assert.equal(await page.locator('#layer-models').isChecked(),true);assert.equal(await page.locator('#layer-plans').isChecked(),true);
    await page.waitForTimeout(150);
    assert.equal(requests.filter(u=>u.endsWith('.webp')).length,0,'no plan imagery before zoom');
    await page.locator('#search').fill('piwnica mietusia');
    await page.locator('[data-object="MTZ-0017"]').first().click();
    await page.getByRole('heading',{name:/Historia pomiarów/}).waitFor();
    assert.match(await page.locator('#object-panel').innerText(),/Best/);
    await page.locator('#tpn-message').waitFor({state:'visible'});
    const mapBox=await page.locator('#map').boundingBox(),panelBox=await page.locator('#sidebar').boundingBox();
    if(mobile)assert.ok(mapBox.y+mapBox.height<=panelBox.y+2,'map remains above mobile panel');
    await page.getByRole('tab',{name:'Warstwy'}).click();
    // Geology uses native PL-1992 WMS requests; pin success/outage independently of PIG uptime.
    let geologyOffline=false;const geologyRequests=[];
    await page.route('https://cbdgmapa.pgi.gov.pl/**',route=>{
      geologyRequests.push(new URL(route.request().url()));
      return geologyOffline?route.abort():route.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#bc8dbc"/></svg>'});
    });
    for(const [value,service,layers] of [['smgt_a_zakryta','smgt_a_zakryta','0,1,2,3,4,5'],['smgt_b_odkryta','smgt_b_odkryta','0,1,2,3,4']]){
      await page.locator('#basemap').selectOption(value,{timeout:3000});
      await waitForDownload(u=>u.includes(`/kartografia/${service}/`),service);
      const request=geologyRequests.find(u=>u.pathname.includes(`/kartografia/${service}/`));
      assert.equal(request.searchParams.get('SRS'),'EPSG:2180');
      assert.equal(request.searchParams.get('LAYERS'),layers);
      const bbox=request.searchParams.get('BBOX').split(',').map(Number);
      assert.ok(bbox[0]>550000&&bbox[0]<590000&&bbox[1]>140000&&bbox[1]<170000,'WMS 1.1.1 uses easting/northing');
      await page.locator('#tpn-message').waitFor({state:'hidden'});
      assert.ok(await page.locator('.ol-attribution').getByText('PIG-PIB',{exact:false}).count());
      const legend=new URL(await page.locator('#geology-legend').getAttribute('href'));
      assert.ok(legend.pathname.includes(`/kartografia/${service}/MapServer/WMSServer`));
      assert.equal(legend.searchParams.get('request'),'GetLegendGraphic');
      assert.equal(legend.searchParams.get('layer'),'0');
    }
    await page.locator('#basemap-opacity').evaluate(el=>{el.value='45';el.dispatchEvent(new Event('input',{bubbles:true}));});
    assert.equal(await page.locator('#base-opacity-value').innerText(),'45%');
    const beforeOutage=new Set(finishedURLs);
    geologyOffline=true;await page.locator('#basemap').selectOption('smgt_a_zakryta');
    // WebKit can reuse decoded images despite routing. Zoom to request uncached tiles.
    await page.locator('.ol-zoom-in').click();
    await page.locator('#tpn-message').waitFor({state:'visible'});
    assert.match(await page.locator('#tpn-message').innerText(),/geologiczn.*OSM/);
    geologyOffline=false;await page.locator('#retry-tpn').click();
    await waitForDownload(u=>u.includes('/kartografia/smgt_a_zakryta/')&&!beforeOutage.has(u),'geology recovered after retry');
    await page.locator('#tpn-message').waitFor({state:'hidden'});
    await page.locator('#basemap').selectOption('osm');
    assert.equal(await page.locator('#base-opacity-value').innerText(),'45%');
    await page.locator('#basemap').selectOption('rgb_2020');
    for(const id of ['other','rejected','differences'])await page.locator(`#layer-${id}`).check();
    await waitForDownload(u=>u.endsWith('measurements.geojson'),'measurements');
    await page.locator('#layer-plans').uncheck();
    await page.getByRole('tab',{name:'Plany',exact:true}).click();
    await page.locator('#plan-search').fill('001197');
    await page.locator('#plan-list [data-plan-fit="001197"]').click();
    const preview=catalog.plans.find(p=>p.id==='001197').preview.url;
    await waitForDownload(u=>u.endsWith(preview),'001197 preview');
    await page.waitForTimeout(250);
    await page.screenshot({path:`output/playwright/${name}-${mobile?'mobile':'desktop'}-whole-plan.png`});
    if(mobile)await page.locator('#panel-toggle').click();
    await page.getByRole('tab',{name:'Plany',exact:true}).click();
    await page.locator('#plan-search').fill('001459');
    await page.locator('#plan-list [data-plan-fit="001459-pza-2024"]').click();
    await waitForDownload(u=>u.endsWith(catalog.plans.find(p=>p.id==='001459-pza-2024').preview.url),'001459-pza-2024 preview');
    for(let i=0;i<3;i++){await page.locator('.ol-zoom-in').click();await page.waitForTimeout(300);}
    console.log('zoomed',name,mobile,await page.locator('#plan-status').innerText());
    await page.screenshot({path:`output/playwright/${name}-${mobile?'mobile':'desktop'}-zoom-debug.png`});
    await waitForDownload(u=>u.includes('/001459-pza-2024/tiles/'),'001459-pza-2024 detail');
    await page.waitForTimeout(500);
    await page.screenshot({path:`output/playwright/${name}-${mobile?'mobile':'desktop'}-detail.png`});
    if(mobile)await page.locator('#panel-toggle').click();
    await page.getByRole('tab',{name:'Plany',exact:true}).click();
    const slider=page.locator('#plan-list [data-plan-opacity="001459-pza-2024"]');await slider.evaluate(el=>{el.value='45';el.dispatchEvent(new Event('input',{bubbles:true}));});assert.equal(await slider.inputValue(),'45');
    await page.locator('#plan-list [data-plan-order="001459-pza-2024"][data-direction="-1"]').click();
    await page.locator('#plan-list [data-plan-toggle="001459-pza-2024"]').uncheck();
    assert.equal(await page.locator('#plan-list [data-plan-toggle="001459-pza-2024"]').isChecked(),false);
    await page.locator('#plan-list [data-plan-info="001459-pza-2024"]').click();await page.getByText('Pochodzenie, transformacja i metadane planu',{exact:true}).waitFor();
    await page.locator('#search').fill('C-0295');await page.locator('[data-cave="C-0295"]').click();await page.getByText('Brak jawnie przypisanego obiektu w tej migawce.',{exact:false}).waitFor();
    await page.getByRole('tab',{name:'Źródła',exact:true}).click();assert.equal(await page.locator('.source-card').count(),3);
    assert.equal(await page.locator('a[href="data/inputs.json"]').count(),1);
    assert.deepEqual(errors,[],`${name}: no JS errors`);
    results.push({engine:name,mobile,dpr:mobile?3:1,readyMs,planRequests:requests.filter(u=>u.endsWith('.webp')).length,resourceTiming:await timing(),errors});
    }catch(error){
     await page.screenshot({path:`output/playwright/${caseName}-failure.png`}).catch(()=>{});
     const failure={engine:name,mobile,error:String(error),errors,network:[...network.values()],resourceTiming:await timing().catch(()=>null)};
     await writeFile(`output/playwright/${caseName}-failure.json`,JSON.stringify(failure,null,2));
     await writeFile('output/playwright/results.json',JSON.stringify([...results,failure],null,2));
     throw error;
    }finally{await context.close();}
   }
  }finally{await browser.close();}
 }
 await writeFile('output/playwright/results.json',JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2));
}finally{server.close();}
