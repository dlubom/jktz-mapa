"""Controlled faults of the disposable probe, not production importer tests."""
import argparse, copy, hashlib, io, json, re, stat, zipfile
from pathlib import Path, PurePosixPath

P=argparse.ArgumentParser();P.add_argument('--root',default='/private/tmp/jktz-input-probe');A=P.parse_args();ROOT=Path(A.root)
def fail(code): raise ValueError(code)
def asset(data,digest):
    if not isinstance(digest,str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',digest):fail('UNSUPPORTED_INTEGRITY_CONTRACT')
    if 'sha256:'+hashlib.sha256(data).hexdigest()!=digest:fail('ASSET_HASH_MISMATCH')
def structure(z):
    names=set()
    for i in z.infolist():
        p=PurePosixPath(i.filename)
        if p.is_absolute() or '..' in p.parts or '\\' in i.filename or stat.S_ISLNK(i.external_attr>>16):fail('UNSAFE_ARCHIVE_PATH')
        if i.filename in names:fail('DUPLICATE_ARCHIVE_PATH')
        names.add(i.filename)
    if z.testzip():fail('ZIP_CRC_MISMATCH')
    return names
def geo(z):
    names=structure(z);m=json.loads(z.read('manifest.json'))
    if (m['schema_version'],m['content_version'],m['release']['version'])!=(1,'t10-content-v1','t11-v2'):fail('UNSUPPORTED_GEO_SCHEMA')
    for f in m['release']['files']:
        if hashlib.sha256(z.read(f['archive_path'])).hexdigest()!=f['sha256']:fail('COMPONENT_HASH_MISMATCH')
def jktz(z):
    names=structure(z)
    for n in names:
        if n.startswith('exports/caves/') and n.endswith('.shp'):
            if any(n[:-4]+ext not in names for ext in ['.shx','.dbf','.prj']):fail('MISSING_SHP_COMPONENT')
def modified(z,replace=None,omit=None):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as w:
        for n in z.namelist():
            if n!=omit:w.writestr(n,replace[n] if replace and n in replace else z.read(n))
    out.seek(0);return zipfile.ZipFile(out)
data=(ROOT/'geotiff-tatry-v0.7.4.zip').read_bytes();base=zipfile.ZipFile(io.BytesIO(data));expected='sha256:'+hashlib.sha256(data).hexdigest()
surveys=zipfile.ZipFile(ROOT/'JKTZ-v1.4.12.zip')
asset(data,expected);geo(base);jktz(surveys)
m=json.loads(base.read('manifest.json'));component=m['release']['files'][0]['archive_path'];bad_m=copy.deepcopy(m);bad_m['schema_version']=999
sidecar=next(n for n in surveys.namelist() if n.startswith('exports/caves/') and n.endswith('.shx'))
cases=[
    ('missing API digest','UNSUPPORTED_INTEGRITY_CONTRACT',lambda:asset(data,None)),
    ('changed downloaded bytes','ASSET_HASH_MISMATCH',lambda:asset(data+b'x',expected)),
    ('changed component, valid ZIP CRC','COMPONENT_HASH_MISMATCH',lambda:geo(modified(base,{component:base.read(component)+b' '}))),
    ('future schema','UNSUPPORTED_GEO_SCHEMA',lambda:geo(modified(base,{'manifest.json':json.dumps(bad_m).encode()}))),
    ('missing SHX','MISSING_SHP_COMPONENT',lambda:jktz(modified(surveys,omit=sidecar))),
]
results=[]
for name,expected_code,fn in cases:
    try:fn()
    except ValueError as e:
        if str(e)!=expected_code:raise
        results.append({'case':name,'expected':expected_code,'actual':str(e),'passed':True})
    else:raise AssertionError('fault was accepted: '+name)
result={'scope':'disposable validation probe, not production importer','positiveControls':3,'negativeControls':results}
(ROOT/'negative-probe.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
