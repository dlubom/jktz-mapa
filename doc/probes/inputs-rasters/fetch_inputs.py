"""Disposable reproduction helper: reads fixed study inputs; never selects Latest.

Needs Python 3.9+, curl, and authenticated gh for the two Git tree reads.
No source checkout, source archive, publishing, or token forwarding to raw URLs.
"""
import argparse, concurrent.futures, hashlib, json, subprocess, urllib.parse, zipfile
from pathlib import Path

P=argparse.ArgumentParser();P.add_argument('--root',default='/private/tmp/jktz-input-probe');P.add_argument('--metadata-only',action='store_true');P.add_argument('--assets-only',action='store_true');A=P.parse_args()
ROOT=Path(A.root);ROOT.mkdir(parents=True,exist_ok=True)
LOCK=json.loads(Path(__file__).with_name('source-lock.json').read_text())
def sha(data): return hashlib.sha256(data).hexdigest()
def download(url,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(['curl','-fsSL','--retry','3',url,'-o',str(path)],check=True)
    return path.read_bytes()
if not A.metadata_only:
    for repo in LOCK:
        for a in repo['assets']:
            temporary=ROOT/(a['name']+'.download')
            with temporary.open('wb') as out:
                subprocess.run(['gh','api',f'repos/{repo["repository"]}/releases/assets/{a["id"]}','-H','Accept: application/octet-stream'],stdout=out,check=True)
            data=temporary.read_bytes()
            if a['digest']!='sha256:'+sha(data): raise ValueError('asset digest mismatch: '+a['name'])
            temporary.replace(ROOT/a['name'])
if A.assets_only:raise SystemExit(0)
with zipfile.ZipFile(ROOT/'geotiff-tatry-v0.7.4.zip') as z: manifest=json.loads(z.read('manifest.json'))
for repo in LOCK:
    name=repo['repository'].split('/')[-1]
    if name not in ['Georeferencer','Jaskiniowy-Kataster-Tatr-Zachodnich']:continue
    tree=json.loads(subprocess.check_output(['gh','api',f'repos/{repo["repository"]}/git/trees/{repo["commit"]}?recursive=1']))
    if tree.get('truncated'):raise ValueError('truncated Git tree is unsupported by this study helper')
    (ROOT/f'{name}-tree.json').write_text(json.dumps(tree,indent=2))
    entries={t['path']:t for t in tree['tree'] if t['type']=='blob'}
    if name=='Georeferencer':
        selected={f'data/caves/{p["dir_id"]}/meta.yaml' for p in manifest['plans']}
        for p in manifest['plans']:
            for suffix in ['source.json','image-identity.json']:
                path=f'data/caves/{p["dir_id"]}/{suffix}'
                if path in entries:selected.add(path)
        target='Georeferencer'
    else:
        selected={'Poligony/OTWORY.SRV.j2','src/jktz/exports/pipeline.py','src/jktz/packaging.py'};target='JKTZ'
    def fetch(path):
        if entries[path]['mode'] not in ['100644','100755']:raise ValueError('non-file Git entry')
        url=f'https://raw.githubusercontent.com/{repo["repository"]}/{repo["commit"]}/'+urllib.parse.quote(path)
        data=download(url,ROOT/'pinned-source'/target/path)
        blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if blob!=entries[path]['sha']:raise ValueError('Git blob mismatch: '+path)
        return len(data)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:sizes=list(pool.map(fetch,sorted(selected)))
    print(name,'selected_files',len(sizes),'selected_bytes',sum(sizes),flush=True)
