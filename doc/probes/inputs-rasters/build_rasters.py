from pathlib import Path
import argparse, hashlib, json, math, time
from osgeo import gdal

gdal.UseExceptions()
gdal.SetCacheMax(128*1024*1024)
P=argparse.ArgumentParser();P.add_argument('--root',default='/private/tmp/jktz-input-probe');P.add_argument('--mode',choices=['preview','pyramid'],default='preview');P.add_argument('--tile',type=int,default=512);P.add_argument('--limit',type=int,default=0);P.add_argument('--resume',action='store_true')
A=P.parse_args();ROOT=Path(A.root);plans=json.loads((ROOT/'inventory.json').read_text())
source_sha256=hashlib.sha256((ROOT/'geotiff-tatry-v0.7.4.zip').read_bytes()).hexdigest()
assert source_sha256=='52a7f5a9238e5f4a2836b61f09cfe403ef101bcc3378fd4a27642f13db62d93b'
keep={'001140','010865','001197','001212','001459-pza-2024'}
if A.limit: plans=sorted(plans,key=lambda p:-p['pixels'])[:A.limit]
T=time.perf_counter()

def source(p):
    d=gdal.Open('/vsizip/'+str(ROOT/'geotiff-tatry-v0.7.4.zip')+'/'+p['path'])
    return gdal.Translate('',d,format='VRT',outputType=gdal.GDT_Byte,scaleParams=[[0,1,0,255]])

def write_rgba(ds,window,path,fmt='WEBP'):
    x,y,w,h=window
    rgba=gdal.Translate('',ds,format='MEM',srcWin=[x,y,w,h],bandList=[1,1,1,2])
    for i,ci in enumerate([gdal.GCI_RedBand,gdal.GCI_GreenBand,gdal.GCI_BlueBand,gdal.GCI_AlphaBand],1):rgba.GetRasterBand(i).SetColorInterpretation(ci)
    dest=str(path) if path else '/vsimem/probe.'+fmt.lower()
    if path: path.parent.mkdir(parents=True,exist_ok=True)
    opts=['LOSSLESS=YES','METHOD=4'] if fmt=='WEBP' else ['ZLEVEL=6']
    out=gdal.Translate(dest,rgba,format=fmt,creationOptions=opts);out=None
    size=Path(dest).stat().st_size if path else gdal.VSIStatL(dest).size
    if not path:gdal.Unlink(dest)
    return size

def geometry(p):
    ex=p['extent'];r=p['resolution'];levels=[]
    for level in range(30):
        w=math.ceil((ex[2]-ex[0])/r);h=math.ceil((ex[3]-ex[1])/r)
        if max(w,h)<=512:break
        levels.append({'level':level,'resolution':r,'width':w,'height':h,'tiles':math.ceil(w/A.tile)*math.ceil(h/A.tile),'pixels':w*h})
        r*=2
    return levels

geometry_rows=[{'id':p['id'],'levels':geometry(p)} for p in plans]
(ROOT/f'pyramid-geometry-{A.tile}.json').write_text(json.dumps(geometry_rows,indent=2))
print(json.dumps({'geometry':{'plans':len(plans),'tileCount':sum(l['tiles'] for p in geometry_rows for l in p['levels']),'pixels':sum(l['pixels'] for p in geometry_rows for l in p['levels'])}}),flush=True)

progress=ROOT/f'{A.mode}-{A.tile}-progress.jsonl'
rows=[json.loads(line) for line in progress.read_text().splitlines()] if A.resume and progress.exists() else []
assert len({r['id'] for r in rows})==len(rows)
completed={r['id'] for r in rows}
if not A.resume:progress.write_text('')
for index,p in enumerate(sorted(plans,key=lambda p: (p['id'] not in keep,-p['pixels']))):
    if p['id'] in completed:continue
    start=time.perf_counter();src=source(p);ex=p['extent'];extw=ex[2]-ex[0];exth=ex[3]-ex[1]
    row={'id':p['id'],'name':p['name'],'extent':ex,'nativeResolution':p['resolution'],'sourcePixels':p['pixels']}
    if A.mode=='preview':
        ratio=min(512/max(extw,exth),1/p['resolution'])
        w=max(1,min(round(extw*ratio),math.floor(extw/p['resolution'])))
        h=max(1,min(round(exth*ratio),math.floor(exth/p['resolution'])))
        dst=gdal.Warp('',src,format='VRT',dstSRS='EPSG:2180',outputBounds=ex,width=w,height=h,resampleAlg='bilinear',dstAlpha=True,outputType=gdal.GDT_Byte)
        path=ROOT/'rasters'/p['id']/'preview-512.webp';size=write_rgba(dst,[0,0,w,h],path)
        row.update({'width':w,'height':h,'pixels':w*h,'bytes':size,'path':str(path.relative_to(ROOT))})
    else:
        row['levels']=[]
        for level in geometry(p):
            r=level['resolution'];w=level['width'];h=level['height'];bounds=[ex[0],ex[3]-h*r,ex[0]+w*r,ex[3]]
            dst=gdal.Warp('',src,format='VRT',dstSRS='EPSG:2180',outputBounds=bounds,width=w,height=h,resampleAlg='bilinear',dstAlpha=True,outputType=gdal.GDT_Byte)
            tile_rows=[];total=0
            for y in range(0,h,A.tile):
                for x in range(0,w,A.tile):
                    tw=min(A.tile,w-x);th=min(A.tile,h-y)
                    path=ROOT/'rasters'/p['id']/f'tiles-{A.tile}'/str(level['level'])/f'{x//A.tile}-{y//A.tile}.webp' if p['id'] in keep else None
                    size=write_rgba(dst,[x,y,tw,th],path);total+=size
                    if path:tile_rows.append({'x':x//A.tile,'y':y//A.tile,'width':tw,'height':th,'bytes':size,'path':str(path.relative_to(ROOT))})
            level.update({'bytes':total,'bounds':bounds})
            if tile_rows:level['tileIndex']=tile_rows
            row['levels'].append(level)
        row['bytes']=sum(l['bytes'] for l in row['levels']);row['tileCount']=sum(l['tiles'] for l in row['levels']);row['pixels']=sum(l['pixels'] for l in row['levels'])
    row['buildSeconds']=time.perf_counter()-start;rows.append(row)
    with (ROOT/f'{A.mode}-{A.tile}-progress.jsonl').open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
    if p['id'] in keep or index%50==0:print(json.dumps({'done':index+1,'id':p['id'],'seconds':row['buildSeconds'],'bytes':row['bytes'],'elapsedSeconds':time.perf_counter()-T}),flush=True)
assert {r['id'] for r in rows}=={p['id'] for p in plans}
result={'mode':A.mode,'tile':A.tile,'gdal':gdal.VersionInfo(),'sourceSha256':source_sha256,'method':'bilinear north-up EPSG:2180; WebP LOSSLESS=YES METHOD=4; edge tiles trimmed; no gutter; all rectangular cells retained','buildSeconds':sum(r['buildSeconds'] for r in rows),'resumed':A.resume,'plans':len(rows),'totalBytes':sum(r['bytes'] for r in rows),'totalPixels':sum(r['pixels'] for r in rows),'tileCount':sum(r.get('tileCount',1) for r in rows),'rows':rows}
(ROOT/f'{A.mode}-{A.tile}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)
