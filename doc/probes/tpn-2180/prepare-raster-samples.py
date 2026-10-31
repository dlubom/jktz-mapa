"""Disposable input: output of inputs-rasters probe, never a sibling checkout."""
import json, pathlib, shutil, sys
root=pathlib.Path(sys.argv[1]); dest=pathlib.Path(__file__).parent/'dist-raster'
selected={'001197','001459-pza-2024','010865','001212','001140'}
previews=json.loads((root/'preview-512.json').read_text())
print(type(previews).__name__)
plans={}
for line in (root/'pyramid-512-progress.jsonl').read_text().splitlines():
    p=json.loads(line)
    if p['id'] not in selected: continue
    for level in p['levels']:level.pop('tileIndex',None)
    # Preview's GDAL extent must be read from its own output, not inferred from source.
    from osgeo import gdal
    ds=gdal.Open(str(root/'rasters'/p['id']/'preview-512.webp'))
    gt=ds.GetGeoTransform();w=ds.RasterXSize;h=ds.RasterYSize
    p['previewExtent']=[gt[0],gt[3]+h*gt[5],gt[0]+w*gt[1],gt[3]]
    plans[p['id']]=p
    shutil.copytree(root/'rasters'/p['id'],dest/'rasters'/p['id'],dirs_exist_ok=True)
(dest/'samples.json').write_text(json.dumps(plans))
