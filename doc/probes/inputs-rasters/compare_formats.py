"""Small native-resolution fragment comparison; not a browser benchmark."""
from pathlib import Path
import argparse, json, math
from osgeo import gdal
import numpy as np

gdal.UseExceptions()
P=argparse.ArgumentParser();P.add_argument('--root',default='/private/tmp/jktz-input-probe');A=P.parse_args();ROOT=Path(A.root)
plans=json.loads((ROOT/'inventory.json').read_text());ids={'001140','010865','001197','001212','001459-pza-2024','001189'}
def save(ds,path,fmt):
    path.parent.mkdir(parents=True,exist_ok=True)
    out=gdal.Translate(str(path),ds,format=fmt,creationOptions=['LOSSLESS=YES','METHOD=4'] if fmt=='WEBP' else ['ZLEVEL=6']);out=None
    check=gdal.Open(str(path)).ReadAsArray();reference=ds.ReadAsArray();opaque=reference[3]>0
    if check.shape[0]==3:check=np.concatenate([check,np.full((1,*check.shape[1:]),255,dtype=np.uint8)])
    assert np.array_equal(check[3],reference[3])
    assert np.array_equal(check[:3,opaque],reference[:3,opaque])
    return path.stat().st_size
rows=[]
for p in plans:
    if p['id'] not in ids:continue
    src=gdal.Translate('',gdal.Open('/vsizip/'+str(ROOT/'geotiff-tatry-v0.7.4.zip')+'/'+p['path']),format='VRT',outputType=gdal.GDT_Byte,scaleParams=[[0,1,0,255]])
    ex=p['extent'];ratio=min(1024/max(ex[2]-ex[0],ex[3]-ex[1]),1/p['resolution']);w=round((ex[2]-ex[0])*ratio);h=round((ex[3]-ex[1])*ratio)
    preview=gdal.Warp('',src,format='MEM',dstSRS='EPSG:2180',outputBounds=ex,width=w,height=h,resampleAlg='bilinear',dstAlpha=True,outputType=gdal.GDT_Byte)
    rgba=gdal.Translate('',preview,format='MEM',bandList=[1,1,1,2])
    for i,ci in enumerate([gdal.GCI_RedBand,gdal.GCI_GreenBand,gdal.GCI_BlueBand,gdal.GCI_AlphaBand],1):rgba.GetRasterBand(i).SetColorInterpretation(ci)
    preview_bytes=save(rgba,ROOT/'rasters'/p['id']/'preview-1024.webp','WEBP')
    cx=(ex[0]+ex[2])/2;cy=(ex[1]+ex[3])/2;r=p['resolution'];bounds=[cx-512*r,cy-512*r,cx+512*r,cy+512*r]
    view=gdal.Warp('',src,format='MEM',dstSRS='EPSG:2180',outputBounds=bounds,width=1024,height=1024,resampleAlg='bilinear',dstAlpha=True,outputType=gdal.GDT_Byte)
    cases=[]
    for tile in [256,512]:
        for fmt in ['WEBP','PNG']:
            total=0
            for y in range(0,1024,tile):
                for x in range(0,1024,tile):
                    ds=gdal.Translate('',view,format='MEM',srcWin=[x,y,tile,tile],bandList=[1,1,1,2])
                    for i,ci in enumerate([gdal.GCI_RedBand,gdal.GCI_GreenBand,gdal.GCI_BlueBand,gdal.GCI_AlphaBand],1):ds.GetRasterBand(i).SetColorInterpretation(ci)
                    total+=save(ds,ROOT/'format-fragments'/p['id']/f'{tile}-{fmt}'/f'{x//tile}-{y//tile}.{fmt.lower()}',fmt)
            cases.append({'tile':tile,'format':fmt,'bytes':total,'tiles':(1024//tile)**2,'rgbaBytes':1024*1024*4,'decodedEqualAtNonzeroAlpha':True})
    rows.append({'id':p['id'],'name':p['name'],'rotation':p['rotation'],'bounds':bounds,'resolution':r,'preview1024':{'width':w,'height':h,'bytes':preview_bytes},'cases':cases})
(ROOT/'format-comparison.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));print(json.dumps(rows,ensure_ascii=False,indent=2))
