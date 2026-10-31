from pathlib import Path, PurePosixPath
from collections import Counter
import argparse, hashlib, json, math, re, sqlite3, stat, zipfile
from osgeo import gdal, ogr

gdal.UseExceptions()
P=argparse.ArgumentParser();P.add_argument('--root',default='/private/tmp/jktz-input-probe');A=P.parse_args()
ROOT=Path(A.root)
def digest(data): return hashlib.sha256(data).hexdigest()
def safe_zip(z):
    names = []
    for i in z.infolist():
        p = PurePosixPath(i.filename)
        if p.is_absolute() or '..' in p.parts or '\\' in i.filename or stat.S_ISLNK(i.external_attr >> 16):
            raise ValueError('unsafe archive member: '+i.filename)
        if i.filename in names: raise ValueError('duplicate member: '+i.filename)
        names.append(i.filename)
    if z.testzip(): raise ValueError('CRC mismatch')
    return names

geo = zipfile.ZipFile(ROOT/'geotiff-tatry-v0.7.4.zip')
safe_zip(geo)
manifest = json.loads(geo.read('manifest.json'))
assert (manifest['schema_version'],manifest['content_version'],manifest['status'],manifest['release']['version'],manifest['geometry']['model']) == (1,'t10-content-v1','complete','t11-v2','t06-local-similarity-v1')
files = manifest['release']['files']
assert len({f['archive_path'] for f in files}) == len(files)
assert len({(f['plan_id'],f['output']) for f in files}) == len(files)
for f in files:
    assert digest(geo.read(f['archive_path'])) == f['sha256'], f['archive_path']
assert set(geo.namelist()) == {'manifest.json'} | {f['archive_path'] for f in files}
paths = {f['plan_id']:f['archive_path'] for f in files if f['output']=='image_georef.tif'}
inventory = []
structures = Counter()
for p in manifest['plans']:
    pid=p['dir_id']; path=paths[pid]
    ds=gdal.Open('/vsizip/'+str(ROOT/'geotiff-tatry-v0.7.4.zip')+'/'+path)
    w,h=ds.RasterXSize,ds.RasterYSize; gt=ds.GetGeoTransform(); b=ds.GetRasterBand(1)
    assert [w,h] == p['acceptance']['size']
    assert list(gt) == p['acceptance']['geotransform']
    assert ds.GetSpatialRef().GetAuthorityCode(None)=='2180'
    corners=[(gt[0]+x*gt[1]+y*gt[2],gt[3]+x*gt[4]+y*gt[5]) for x,y in [(0,0),(w,0),(w,h),(0,h)]]
    extent=[min(x for x,y in corners),min(y for x,y in corners),max(x for x,y in corners),max(y for x,y in corners)]
    structure=(ds.RasterCount,ds.GetMetadata('IMAGE_STRUCTURE').get('COMPRESSION'),b.GetMetadata('IMAGE_STRUCTURE').get('NBITS'),b.GetOverviewCount())
    structures[str(structure)]+=1
    inventory.append({'id':pid,'name':p['measurement']['name_local'],'path':path,'width':w,'height':h,'pixels':w*h,'rgbaBytes':w*h*4,'tiffBytes':geo.getinfo(path).file_size,'geotransform':gt,'extent':extent,'resolution':math.hypot(gt[1],gt[4]),'rotation':p['parameters']['total_rotation_deg']})
inventory.sort(key=lambda p:p['pixels'])
(ROOT/'inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2))

expected_meta={f'data/caves/{p["dir_id"]}/meta.yaml':p['inputs']['meta.yaml'] for p in manifest['plans']}
source_meta={}; optional={}; source_stats=[]
for repo,folder in [('Georeferencer','Georeferencer'),('Jaskiniowy-Kataster-Tatr-Zachodnich','JKTZ')]:
    tree=json.loads((ROOT/f'{repo}-tree.json').read_text())
    assert not tree.get('truncated')
    blobs={e['path']:e for e in tree['tree'] if e['type']=='blob'}
    for local in sorted((ROOT/'pinned-source'/folder).rglob('*')):
        if not local.is_file(): continue
        path=local.relative_to(ROOT/'pinned-source'/folder).as_posix();data=local.read_bytes()
        actual_blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        assert actual_blob==blobs[path]['sha'],path
        item={'sha256':digest(data),'git_blob_sha1':actual_blob,'bytes':len(data)}
        if folder=='Georeferencer':
            if path in expected_meta:
                assert digest(data)==expected_meta[path],path
                source_meta[path]=item
            else: optional[path]=item
assert source_meta.keys()==expected_meta.keys()
(ROOT/'pinned-meta.json').write_text(json.dumps({'required':source_meta,'optional':optional,'source_archive':source_stats},indent=2))

gps_zip=zipfile.ZipFile(ROOT/'katalog.sqlite.zip');safe_zip(gps_zip)
db=ROOT/'katalog.sqlite';db.write_bytes(gps_zip.read('katalog.sqlite'))
con=sqlite3.connect(f'file:{db}?mode=ro',uri=True)
tables=[r[0] for r in con.execute("select name from sqlite_master where type='table'")]
ddl={t:con.execute('pragma table_info('+t+')').fetchall() for t in tables}
counts={t:con.execute('select count(*) from '+t).fetchone()[0] for t in tables}
assert con.execute('pragma integrity_check').fetchone()[0]=='ok'
gps={'metadataAsset':json.loads((ROOT/'metadata.json').read_text()),'ddl':ddl,'counts':counts,'metadataTable':con.execute('select * from metadata').fetchall(),'foreignKeyErrors':con.execute('pragma foreign_key_check').fetchall()}
(ROOT/'gps-profile.json').write_text(json.dumps(gps,indent=2))

jktz=zipfile.ZipFile(ROOT/'JKTZ-v1.4.12.zip');names=safe_zip(jktz)
shps=[n for n in names if n.startswith('exports/caves/') and n.endswith('.shp')]
models=[]
for shp in shps:
    for ext in ['.shx','.dbf','.prj']: assert shp[:-4]+ext in names
    ds=ogr.Open('/vsizip/'+str(ROOT/'JKTZ-v1.4.12.zip')+'/'+shp);ly=ds.GetLayer(0)
    sr=ly.GetSpatialRef();sr.AutoIdentifyEPSG()
    models.append({'path':shp,'features':ly.GetFeatureCount(),'geometry':ogr.GeometryTypeToName(ly.GetGeomType()),'epsg':sr.GetAuthorityCode(None),'fields':[ly.GetLayerDefn().GetFieldDefn(i).GetName() for i in range(ly.GetLayerDefn().GetFieldCount())]})
(ROOT/'jktz-profile.json').write_text(json.dumps(models,indent=2))
summary={'archiveFiles':len(geo.namelist()),'hashesVerified':len(files),'metaVerified':len(source_meta),'optionalMetadataFiles':len(optional),'structures':dict(structures),'plans':len(inventory),'pixels':sum(p['pixels'] for p in inventory),'tiffBytes':sum(p['tiffBytes'] for p in inventory),'rgbaBytes':sum(p['rgbaBytes'] for p in inventory),'over100MiBRgba':sum(p['rgbaBytes']>100*1024**2 for p in inventory),'percentileFloor':{str(q):inventory[int((len(inventory)-1)*q)] for q in [.5,.95,1]},'jktzModels':len(models),'jktzFeatures':sum(p['features'] for p in models),'gpsCounts':counts,'sourceArchive':source_stats}
(ROOT/'input-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False,indent=2))
