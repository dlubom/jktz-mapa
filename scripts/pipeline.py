#!/usr/bin/env python3
"""Build the static map from three pinned public releases, without source checkouts.

resolve performs the only Latest lookups. fetch/build accept that immutable lock.
The source contracts and render profile are versioned here, not inferred by name.
"""
from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
import multiprocessing
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
import urllib.parse
import zipfile

import raster_cache as raster_store

PROFILE = 'map-data-v1-webp512-gutter1'
REPOSITORIES = {
    'jktz': 'dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich',
    'gps': 'dlubom/gps-kataster-obiektow-tatr',
    'geo': 'dlubom/Georeferencer',
}
TILE_SIZE = 512
GUTTER = 1


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def json_read(data):
    return json.loads(data, object_pairs_hook=unique_pairs)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def api(path):
    return json_read(subprocess.check_output(['gh', 'api', path]))


def safe_id(value):
    require(isinstance(value, str) and re.fullmatch(r'[\w.-]+', value, re.ASCII) and value not in ('.', '..'), f'Unsafe identifier: {value}')
    return value


def validate_asset(asset, data):
    require(re.fullmatch(r'sha256:[0-9a-f]{64}', asset.get('digest', '')) is not None, 'UNSUPPORTED_INTEGRITY_CONTRACT')
    require(len(data) == asset['size'], f'ASSET_SIZE_MISMATCH: {asset["name"]}')
    require('sha256:' + digest(data) == asset['digest'], f'ASSET_HASH_MISMATCH: {asset["name"]}')


def safe_archive(archive):
    names = set()
    total = 0
    for info in archive.infolist():
        name = info.filename
        parts = name.split('/')
        require(not name.startswith('/') and '\\' not in name and not any(p in ('.', '..') for p in parts), f'Unsafe ZIP path: {name}')
        require(not stat.S_ISLNK(info.external_attr >> 16), f'ZIP symlink: {name}')
        require(name not in names, f'Duplicate ZIP member: {name}')
        names.add(name)
        total += info.file_size
    require(total <= 4 * 1024**3, 'Unsupported ZIP expanded size (>4 GiB)')
    require(archive.testzip() is None, 'ZIP CRC mismatch')
    return names


def resolve(lock_path):
    require(not lock_path.exists(), f'Inputs already pinned: {lock_path}; use a new path for a new Run')
    sources = []
    for key, repository in REPOSITORIES.items():
        release = api(f'repos/{repository}/releases/latest')
        require(not release['draft'] and not release['prerelease'], f'Latest is not stable: {repository}')
        tag = release['tag_name']
        obj = api(f'repos/{repository}/git/ref/tags/{urllib.parse.quote(tag, safe="")}')['object']
        chain = [obj]
        while obj['type'] == 'tag':
            require(len(chain) < 16, 'Tag chain too deep')
            obj = api(f'repos/{repository}/git/tags/{obj["sha"]}')['object']
            chain.append(obj)
        require(obj['type'] == 'commit', f'Tag does not resolve to commit: {repository}')
        names = {'jktz': [f'JKTZ-{tag}.zip'], 'gps': ['katalog.sqlite.zip', 'metadata.json'], 'geo': [f'geotiff-tatry-{tag}.zip']}[key]
        assets = []
        for name in names:
            selected = [a for a in release['assets'] if a['name'] == name]
            require(len(selected) == 1, f'Missing or ambiguous asset: {repository}/{name}')
            a = selected[0]
            require(re.fullmatch(r'sha256:[0-9a-f]{64}', a.get('digest') or ''), f'UNSUPPORTED_INTEGRITY_CONTRACT: {name}')
            assets.append({k: a[k] for k in ['id', 'name', 'size', 'digest', 'browser_download_url']})
        tree = api(f'repos/{repository}/git/trees/{obj["sha"]}?recursive=1')
        require(not tree.get('truncated'), f'Truncated tree: {repository}')
        files = []
        for entry in tree['tree']:
            path = entry['path']
            selected = ('/' not in path and re.fullmatch(r'LICEN[CS]E(?:\..*)?', path, re.IGNORECASE))
            if key == 'jktz':
                selected = selected or path == 'Poligony/OTWORY.SRV.j2'
            if key == 'geo':
                selected = selected or bool(re.fullmatch(r'data/caves/[^/]+/(meta.yaml|source.json|image-identity.json)', path))
            if selected:
                require(entry['type'] == 'blob' and entry['mode'] in ('100644', '100755'), f'Unsupported source entry: {path}')
                files.append({'path': path, 'gitBlobSha1': entry['sha'], 'size': entry['size']})
        if key == 'jktz':
            require(any(f['path'] == 'Poligony/OTWORY.SRV.j2' for f in files), 'Missing JKTZ relations template')
        sources.append({'key': key, 'repository': repository, 'tag': tag, 'commit': obj['sha'], 'tagChain': chain,
                        'releaseId': release['id'], 'url': release['html_url'], 'publishedAt': release['published_at'],
                        'draft': False, 'prerelease': False, 'assets': assets, 'files': files})
        print(f'Pinned {key}: {tag} {obj["sha"]}', flush=True)
    lock = {'schemaVersion': 1, 'profile': PROFILE, 'resolvedAt': datetime.now(timezone.utc).isoformat(), 'sources': sources}
    write_json(lock_path, lock)


def read_lock(path):
    lock = json_read(path.read_bytes())
    require(lock['schemaVersion'] == 1 and lock['profile'] == PROFILE, 'Unsupported inputs/profile')
    require({s['key'] for s in lock['sources']} == set(REPOSITORIES) and len(lock['sources']) == 3, 'Expected exactly three pinned sources')
    for source in lock['sources']:
        require(source['repository'] == REPOSITORIES[source['key']], 'Unexpected source repository')
        require(not source['draft'] and not source['prerelease'], 'Unstable pinned release')
        require(re.fullmatch('[a-f0-9]{40}', source['commit']), 'Missing commit pin')
        for a in source['assets']:
            safe_id(a['name'])
        for f in source['files']:
            p = PurePosixPath(f['path'])
            require(not p.is_absolute() and '..' not in p.parts and '\\' not in f['path'], 'Invalid pinned path')
    return lock


def source_path(cache, source, path):
    return cache / 'source' / source['key'] / source['commit'] / path


def verify_blob(entry, data):
    actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    require(actual == entry['gitBlobSha1'] and len(data) == entry['size'], f'Git blob mismatch: {entry["path"]}')
    return {'path': entry['path'], 'gitBlobSha1': actual, 'sha256': digest(data), 'size': len(data)}


def fetch(lock, cache):
    cache.mkdir(parents=True, exist_ok=True)
    evidence = []
    for source in lock['sources']:
        for asset in source['assets']:
            path = cache / asset['name']
            matches_pin = path.exists() and path.stat().st_size == asset['size'] and ('sha256:' + digest(path.read_bytes())) == asset['digest']
            if not matches_pin:
                temporary = path.with_suffix(path.suffix + '.download')
                with temporary.open('wb') as stream:
                    subprocess.run(['gh', 'api', f'repos/{source["repository"]}/releases/assets/{asset["id"]}', '-H', 'Accept: application/octet-stream'], stdout=stream, check=True)
                validate_asset(asset, temporary.read_bytes())
                temporary.replace(path)
            data = path.read_bytes()
            validate_asset(asset, data)
            evidence.append({'source': source['key'], 'name': asset['name'], 'expectedDigest': asset['digest'], 'actualSha256': digest(data), 'verified': True})
        def fetch_file(entry):
            path = source_path(cache, source, entry['path'])
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = path.with_suffix(path.suffix + '.download')
                url = f'https://raw.githubusercontent.com/{source["repository"]}/{source["commit"]}/' + urllib.parse.quote(entry['path'])
                subprocess.run(['curl', '-fsSL', '--retry', '3', '--max-time', '60', url, '-o', str(temporary)], check=True)
                verify_blob(entry, temporary.read_bytes())
                temporary.replace(path)
            return verify_blob(entry, path.read_bytes())
        with ThreadPoolExecutor(max_workers=6) as pool:
            rows = list(pool.map(fetch_file, source['files']))
        evidence.append({'source': source['key'], 'files': rows})
        print(f'Verified {source["key"]}: {len(source["assets"])} assets, {len(rows)} source files', flush=True)
    write_json(cache / 'verification.json', evidence)


def collection(features):
    return {'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:2180'}}, 'features': features}


def feature(geometry, properties):
    return {'type': 'Feature', 'geometry': geometry, 'properties': properties}


def coordinate(record, prefix=''):
    east, north = record.get(prefix + 'y_1992'), record.get(prefix + 'x_1992')
    if east is None and north is None:
        return None
    require(isinstance(east, (int, float)) and isinstance(north, (int, float)) and math.isfinite(east) and math.isfinite(north), 'Invalid source coordinate')
    return [east, north]


def import_gps(cache, source, out):
    metadata = json_read((cache / 'metadata.json').read_bytes())
    require(metadata['metadata_schema_version'] == 1 and metadata['data_schema_version'] == 1, 'Unsupported GPS metadata schema')
    with zipfile.ZipFile(cache / 'katalog.sqlite.zip') as archive:
        require('katalog.sqlite' in safe_archive(archive), 'Missing katalog.sqlite')
        db = cache / 'katalog.sqlite'
        db.write_bytes(archive.read('katalog.sqlite'))
    con = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    try:
        require(con.execute('pragma integrity_check').fetchone()[0] == 'ok', 'GPS database integrity error')
        require(not con.execute('pragma foreign_key_check').fetchall(), 'GPS foreign key error')
        names = ['objects', 'caves', 'measurements', 'best_measurements', 'object_external_refs', 'cave_external_refs', 'relations', 'attachments', 'metadata', 'validation_flags']
        tables = {name: [dict(r) for r in con.execute(f'select * from {name}')] for name in names}
    finally:
        con.close()
    meta = {r['key']: r['value'] for r in tables['metadata']}
    require(meta.get('schema_version') == '1', 'Unsupported GPS SQLite schema')
    caves = {r['id']: r for r in tables['caves']}
    best = {r['object_id']: r for r in tables['best_measurements']}
    measurements = defaultdict(list)
    seen = set()
    for row in tables['measurements']:
        key = (row['object_id'], row['id'])
        require(key not in seen, 'Duplicate measurement key')
        seen.add(key)
        measurements[row['object_id']].append(row)
    objects, details, points, differences = [], {}, [], []
    for obj in tables['objects']:
        oid = safe_id(obj['id'])
        choice = best.get(oid)
        require(choice is not None and (oid, choice['measurement_id']) in seen, f'Invalid Best reference: {oid}')
        chosen = next(m for m in measurements[oid] if m['id'] == choice['measurement_id'])
        best_xy = coordinate(chosen)
        require(obj['best_measurement_id'] == choice['measurement_id'], f'Inconsistent Best reference: {oid}')
        cave = caves.get(obj['cave_id'])
        refs = [r for r in tables['object_external_refs'] if r['object_id'] == oid]
        cave_refs = [r for r in tables['cave_external_refs'] if r['cave_id'] == obj['cave_id']]
        rows = []
        for measurement in measurements[oid]:
            xy = coordinate(measurement)
            role = 'best' if measurement['id'] == choice['measurement_id'] else ('rejected' if measurement['verification_status'] == 'odrzucony' else 'other')
            distance = math.dist(best_xy, xy) if xy is not None and best_xy is not None else None
            row = {**measurement, 'coordinate': xy, 'role': role, 'differenceM': distance}
            rows.append(row)
            props = {'objectId': oid, 'id': measurement['id'], 'name': obj['name_local'], 'role': role, 'source': measurement['source'], 'status': measurement['verification_status'], 'differenceM': distance, 'horizontalAccuracy': measurement['horizontal_accuracy_m']}
            if xy is not None:
                points.append(feature({'type': 'Point', 'coordinates': xy}, props))
                if role != 'best' and best_xy is not None:
                    differences.append(feature({'type': 'LineString', 'coordinates': [best_xy, xy]}, props))
        details[oid] = {'object': obj, 'cave': cave, 'best': choice, 'measurements': rows, 'externalRefs': refs, 'caveExternalRefs': cave_refs,
                        'relations': [r for r in tables['relations'] if oid in (r['from_object_id'], r['to_object_id'])],
                        'attachments': [r for r in tables['attachments'] if r['object_id'] == oid], 'modelIds': [], 'planIds': []}
        search = [obj['name_local'], oid, obj['cave_id'], cave.get('name') if cave else '', cave.get('system_name') if cave else '', obj.get('notes'), cave.get('notes') if cave else '']
        search.extend(r['external_id'] for r in refs + cave_refs)
        objects.append({'id': oid, 'name': obj['name_local'], 'caveId': obj['cave_id'], 'caveName': cave['name'] if cave else None, 'systemName': cave['system_name'] if cave else None,
                        'coordinate': best_xy, 'searchText': ' '.join(str(v) for v in search if v),
                        'best': {'id': choice['measurement_id'], 'source': chosen['source'], 'verificationStatus': chosen['verification_status'], 'horizontalAccuracy': chosen['horizontal_accuracy_m']},
                        'detailUrl': f'data/objects/{oid}.json', 'modelIds': [], 'planIds': []})
    cave_entries = []
    for cave in tables['caves']:
        cid = safe_id(cave['id'])
        refs = [r for r in tables['cave_external_refs'] if r['cave_id'] == cid]
        object_ids = [obj['id'] for obj in tables['objects'] if obj['cave_id'] == cid]
        search = [cid, cave.get('name'), cave.get('system_name'), cave.get('notes')]
        search.extend(r['external_id'] for r in refs)
        cave_entries.append({'id': cid, 'name': cave['name'], 'systemName': cave.get('system_name'), 'objectIds': object_ids,
                             'searchText': ' '.join(str(v) for v in search if v), 'detailUrl': f'data/caves/{cid}.json'})
        write_json(out / 'caves' / f'{cid}.json', {'cave': cave, 'externalRefs': refs, 'objectIds': object_ids})
    write_json(out / 'caves.json', cave_entries)
    write_json(out / 'measurements.geojson', collection(points))
    write_json(out / 'differences.geojson', collection(differences))
    write_json(out / 'gps-source-metadata.json', {'releaseMetadata': metadata, 'databaseMetadata': tables['metadata'], 'validationFlags': tables['validation_flags']})
    return objects, details, {'objects': len(objects), 'caves': len(caves), 'measurements': len(points), 'sourceMeasurements': len(tables['measurements']), 'best': len(best)}


def parse_relations(template):
    """Read literal arguments with Python's parser; never evaluate the template."""
    result = defaultdict(list)
    for line in template.splitlines():
        if line.lstrip().startswith(';'):
            continue
        match = re.match(r'^\s*\{\{\s*(gps_fix\(.*\))\s*\}\}', line)
        if match:
            node = ast.parse(match.group(1), mode='eval').body
            require(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'gps_fix', 'Unsupported relation call')
            require(len(node.args) >= 2 and all(isinstance(arg, ast.Constant) and isinstance(arg.value, str) for arg in node.args[:2]), 'Nonliteral relation arguments')
            station, oid = (arg.value for arg in node.args[:2])
            result[station.split(':', 1)[0]].append({'station': station, 'objectId': oid})
        elif 'gps_fix(' in line and not line.lstrip().startswith(('#', '{#')):
            raise ValueError('Unsupported active gps_fix syntax')
    return dict(result)


def extent_of_coordinates(coordinates):
    points = []
    def walk(value):
        if value and isinstance(value[0], (int, float)):
            points.append(value)
        else:
            for item in value:
                walk(item)
    walk(coordinates)
    require(bool(points), 'Empty geometry')
    require(all(math.isfinite(n) for p in points for n in p), 'Non-finite geometry')
    return [min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)]


def union_extent(extents):
    require(bool(extents), 'No extents')
    return [min(e[0] for e in extents), min(e[1] for e in extents), max(e[2] for e in extents), max(e[3] for e in extents)]


def import_jktz(cache, source, out, details):
    from osgeo import ogr, osr
    ogr.UseExceptions()
    osr.UseExceptions()
    archive_path = cache / source['assets'][0]['name']
    with zipfile.ZipFile(archive_path) as archive:
        names = safe_archive(archive)
    paths = sorted(n for n in names if n.startswith('exports/caves/') and n.endswith('.shp'))
    require(paths, 'Missing JKTZ cave exports')
    template = source_path(cache, source, 'Poligony/OTWORY.SRV.j2').read_text()
    relations = parse_relations(template)
    write_json(out / 'jktz-relations.json', {'sourcePath': 'Poligony/OTWORY.SRV.j2', 'commit': source['commit'], 'models': relations})
    target = osr.SpatialReference()
    target.ImportFromEPSG(2180)
    target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    models = []
    for path in paths:
        mid = safe_id(PurePosixPath(path).stem)
        for ext in ('.dbf', '.prj', '.shx'):
            require(path[:-4] + ext in names, f'Missing SHP component: {path[:-4] + ext}')
        ds = ogr.Open('/vsizip/' + str(archive_path.resolve()) + '/' + path)
        require(ds is not None, f'Cannot open SHP: {path}')
        layer = ds.GetLayer(0)
        sr = layer.GetSpatialRef()
        require(sr is not None, f'Missing CRS: {path}')
        sr.AutoIdentifyEPSG()
        require(sr.GetAuthorityCode(None) == '32634', f'Unsupported JKTZ CRS: {path}')
        sr.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        transform = osr.CoordinateTransformation(sr, target)
        features, extents = [], []
        for item in layer:
            geom = item.GetGeometryRef().Clone()
            require(geom.GetCoordinateDimension() == 3 and ogr.GT_Flatten(geom.GetGeometryType()) in (ogr.wkbLineString, ogr.wkbMultiLineString), f'Unsupported JKTZ geometry: {path}')
            original = json_read(geom.ExportToJson())
            require(geom.Transform(transform) == 0, 'JKTZ reprojection failed')
            geometry = json_read(geom.ExportToJson())
            properties = dict(item.items())
            properties.update({'modelId': mid, 'sourceCrs': 'EPSG:32634', 'sourceGeometry': original})
            features.append(feature(geometry, properties))
            extents.append(extent_of_coordinates(geometry['coordinates']))
        require(features, f'Empty JKTZ model: {mid}')
        object_ids = list(dict.fromkeys(r['objectId'] for r in relations.get(mid, [])))
        for oid in object_ids:
            if oid in details:
                details[oid]['modelIds'].append(mid)
        names_for_model = [details[oid]['object']['name_local'] for oid in object_ids if oid in details]
        name = ' / '.join(dict.fromkeys(names_for_model)) or mid
        models.append({'id': mid, 'name': name, 'extent': union_extent(extents), 'objectIds': object_ids, 'url': f'data/models/{mid}.geojson', 'featureCount': len(features)})
        write_json(out / 'models' / f'{mid}.geojson', collection(features))
    return models


def read_yaml(data):
    import yaml
    class UniqueLoader(yaml.SafeLoader):
        pass
    def mapping(loader, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            require(key not in result, f'Duplicate YAML key: {key}')
            result[key] = loader.construct_object(value_node, deep=deep)
        return result
    UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    # Dates stay strings; identifiers such as 001459 are also retained verbatim.
    UniqueLoader.yaml_implicit_resolvers = {k: [(tag, exp) for tag, exp in v if tag != 'tag:yaml.org,2002:timestamp'] for k, v in UniqueLoader.yaml_implicit_resolvers.items()}
    def integer(loader, node):
        value = loader.construct_scalar(node)
        if re.fullmatch(r'0[0-9]+', value):
            return value
        return yaml.constructor.SafeConstructor.construct_yaml_int(loader, node)
    UniqueLoader.add_constructor('tag:yaml.org,2002:int', integer)
    return yaml.load(data, Loader=UniqueLoader)


def raster_geometry(transform, width, height):
    corners = [(transform[0] + x * transform[1] + y * transform[2], transform[3] + x * transform[4] + y * transform[5]) for x, y in ((0, 0), (width, 0), (width, height), (0, height))]
    extent = extent_of_coordinates(corners)
    resolution = math.hypot(transform[1], transform[4])
    require(resolution > 0 and math.isfinite(resolution), 'Invalid raster resolution')
    levels = []
    r = resolution
    for level in range(30):
        w = math.ceil((extent[2] - extent[0]) / r)
        h = math.ceil((extent[3] - extent[1]) / r)
        if max(w, h) <= TILE_SIZE:
            break
        levels.append({'level': level, 'resolution': r, 'width': w, 'height': h, 'columns': math.ceil(w / TILE_SIZE), 'rows': math.ceil(h / TILE_SIZE),
                       'origin': [extent[0], extent[3]], 'extent': [extent[0], extent[3] - h * r, extent[0] + w * r, extent[3]]})
        r *= 2
    return extent, resolution, levels


def write_webp(dataset, path, window=None):
    from osgeo import gdal
    path.parent.mkdir(parents=True, exist_ok=True)
    if window is None:
        rgba = gdal.Translate('', dataset, format='MEM', bandList=[1, 1, 1, 2])
    else:
        x, y, w, h = window
        left, top = max(x, 0), max(y, 0)
        right, bottom = min(x + w, dataset.RasterXSize), min(y + h, dataset.RasterYSize)
        rgba = gdal.GetDriverByName('MEM').Create('', w, h, 4, gdal.GDT_Byte)
        if right > left and bottom > top:
            data = dataset.ReadRaster(left, top, right - left, bottom - top, band_list=[1, 1, 1, 2])
            rgba.WriteRaster(left - x, top - y, right - left, bottom - top, data)
    for i, ci in enumerate((gdal.GCI_RedBand, gdal.GCI_GreenBand, gdal.GCI_BlueBand, gdal.GCI_AlphaBand), 1):
        rgba.GetRasterBand(i).SetColorInterpretation(ci)
    result = gdal.Translate(str(path), rgba, format='WEBP', creationOptions=['LOSSLESS=YES', 'METHOD=4'])
    require(result is not None, f'WebP write failed: {path}')
    result = None
    return path.stat().st_size


def raster_key(lock):
    source = next(source for source in lock['sources'] if source['key'] == 'geo')
    return raster_store.key(source, PROFILE, __file__)


def render_plan(task):
    """One independent process owns all GDAL datasets for one plan."""
    from osgeo import gdal
    gdal.UseExceptions()
    gdal.SetCacheMax(128 * 1024**2)
    archive, member, target = task
    ds = gdal.Open('/vsizip/' + archive + '/' + member)
    require(ds is not None, f'Unreadable TIFF: {member}')
    extent, resolution, levels = raster_geometry(ds.GetGeoTransform(), ds.RasterXSize, ds.RasterYSize)
    src = gdal.Translate('', ds, format='VRT', outputType=gdal.GDT_Byte, scaleParams=[[0, 1, 0, 255]])
    ew, eh = extent[2] - extent[0], extent[3] - extent[1]
    ratio = min(TILE_SIZE / max(ew, eh), 1 / resolution)
    pw, ph = max(1, math.floor(ew * ratio)), max(1, math.floor(eh * ratio))
    preview = gdal.Warp('', src, format='VRT', dstSRS='EPSG:2180', outputBounds=extent, width=pw, height=ph, resampleAlg='bilinear', dstAlpha=True, outputType=gdal.GDT_Byte)
    write_webp(preview, Path(target) / 'preview.webp')
    for level in levels:
        warped = gdal.Warp('', src, format='VRT', dstSRS='EPSG:2180', outputBounds=level['extent'], width=level['width'], height=level['height'], resampleAlg='bilinear', dstAlpha=True, outputType=gdal.GDT_Byte)
        for y in range(level['rows']):
            for x in range(level['columns']):
                path = Path(target) / 'tiles' / str(level['level']) / f'{x}-{y}.webp'
                write_webp(warped, path, (x * TILE_SIZE - GUTTER, y * TILE_SIZE - GUTTER, TILE_SIZE + 2 * GUTTER, TILE_SIZE + 2 * GUTTER))
    return member


def render_plans(tasks, workers):
    require(type(workers) is int and 1 <= workers <= 4, 'Workers must be between 1 and 4')
    if workers == 1:
        for task in tasks:
            render_plan(task)
    else:
        # spawn avoids inheriting native handles/locks from the validating parent.
        with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('spawn'),
                                 initializer=configure_renderer, initargs=(raster_store.configuration(),)) as pool:
            for index, _ in enumerate(pool.map(render_plan, tasks), 1):
                if index % 50 == 0 or index == len(tasks):
                    print(f'Rendered plans {index}/{len(tasks)} ({workers} workers)', flush=True)


def configure_renderer(config):
    from osgeo import gdal
    for name, value in config.items():
        gdal.SetConfigOption(name, value)


def import_plans(cache, source, out, details, *, workers=None, raster_cache=None):
    from osgeo import gdal
    gdal.UseExceptions()
    gdal.SetCacheMax(128 * 1024**2)
    require(gdal.GetDriverByName('WEBP') is not None, 'GDAL WebP driver is required')
    archive_path = cache / source['assets'][0]['name']
    workers = min(4, os.cpu_count() or 1) if workers is None else workers
    require(type(workers) is int and 1 <= workers <= 4, 'Workers must be between 1 and 4')
    plans, tasks = [], []
    with zipfile.ZipFile(archive_path) as archive:
        names = safe_archive(archive)
        manifest = json_read(archive.read('manifest.json'))
        require((manifest['schema_version'], manifest['content_version'], manifest['status'], manifest['release']['version'], manifest['geometry']['model']) == (1, 't10-content-v1', 'complete', 't11-v2', 't06-local-similarity-v1'), 'Unsupported Georeferencer schema')
        files = manifest['release']['files']
        require(len({f['archive_path'] for f in files}) == len(files), 'Duplicate Geo archive mapping')
        require(len({(f['plan_id'], f['output']) for f in files}) == len(files), 'Duplicate Geo output mapping')
        require(names == {'manifest.json'} | {f['archive_path'] for f in files}, 'Unexpected/missing Geo archive contents')
        for entry in files:
            require(digest(archive.read(entry['archive_path'])) == entry['sha256'], f'Geo component hash mismatch: {entry["archive_path"]}')
        mapping = {(f['plan_id'], f['output']): f for f in files}
        require(len({p['dir_id'] for p in manifest['plans']}) == len(manifest['plans']), 'Duplicate plan ID')
        for index, plan in enumerate(manifest['plans']):
            pid = safe_id(plan['dir_id'])
            entry = mapping[(pid, 'image_georef.tif')]
            ds = gdal.Open('/vsizip/' + str(archive_path.resolve()) + '/' + entry['archive_path'])
            require(ds is not None, f'Unreadable TIFF: {pid}')
            require(ds.GetSpatialRef().GetAuthorityCode(None) == '2180', f'Unsupported plan CRS: {pid}')
            require(ds.RasterCount == 1 and ds.GetRasterBand(1).GetMetadata('IMAGE_STRUCTURE').get('NBITS') == '1', f'Unsupported TIFF profile: {pid}')
            w, h, gt = ds.RasterXSize, ds.RasterYSize, list(ds.GetGeoTransform())
            require([w, h] == plan['acceptance']['size'] and gt == plan['acceptance']['geotransform'] and plan['acceptance']['crs'] == 'EPSG:2180', f'Raster acceptance mismatch: {pid}')
            extent, resolution, levels = raster_geometry(gt, w, h)
            meta_path = f'data/caves/{pid}/meta.yaml'
            meta_bytes = source_path(cache, source, meta_path).read_bytes()
            require(digest(meta_bytes) == plan['inputs']['meta.yaml'], f'Meta hash mismatch: {pid}')
            meta = read_yaml(meta_bytes)
            source_files = [{'path': meta_path, 'sha256': digest(meta_bytes), 'url': f'https://github.com/{source["repository"]}/blob/{source["commit"]}/{meta_path}'}]
            optional = {}
            for suffix, key in [('source.json', 'source'), ('image-identity.json', 'imageIdentity')]:
                path = f'data/caves/{pid}/{suffix}'
                local = source_path(cache, source, path)
                if local.exists():
                    data = local.read_bytes()
                    optional[key] = json_read(data)
                    source_files.append({'path': path, 'sha256': digest(data), 'url': f'https://github.com/{source["repository"]}/blob/{source["commit"]}/{path}'})
            # Relations originate in manifest measurement / explicit metadata, never spatial matching.
            object_ids = list(dict.fromkeys(str(v) for v in [plan.get('measurement', {}).get('object_id'), meta.get('coordinates', {}).get('gps_kataster_object_id')] if v))
            for oid in object_ids:
                if oid in details:
                    details[oid]['planIds'].append(pid)
            name = str(meta.get('cave', {}).get('name') or plan['measurement']['name_local'] or pid)
            ew, eh = extent[2] - extent[0], extent[3] - extent[1]
            ratio = min(TILE_SIZE / max(ew, eh), 1 / resolution)
            pw, ph = max(1, math.floor(ew * ratio)), max(1, math.floor(eh * ratio))
            tasks.append((str(archive_path.resolve()), entry['archive_path'], str(out / 'plans' / pid)))
            ds = None
            write_json(out / 'plans' / pid / 'details.json', {'plan': plan, 'meta': meta, **optional,
                       'computed': json_read(archive.read(mapping[(pid, 'computed.json')]['archive_path'])),
                       'worldFile': archive.read(mapping[(pid, 'image.tfw')]['archive_path']).decode(),
                       'sourceFiles': source_files, 'sourceAsset': {'name': source['assets'][0]['name'], 'archivePath': entry['archive_path'], 'sha256': entry['sha256']},
                       'rendering': {'profile': PROFILE, 'sourceCrs': 'EPSG:2180', 'sourceGeotransform': gt, 'sourceSize': [w, h], 'resampling': 'bilinear', 'format': 'WebP lossless'}})
            plans.append({'id': pid, 'name': name, 'extent': extent, 'nativeResolution': resolution, 'objectIds': object_ids,
                          'sourceCaveId': str(meta['cave']['source_cave_id']) if meta.get('cave', {}).get('source_cave_id') is not None else None,
                          'preview': {'url': f'data/plans/{pid}/preview.webp', 'width': pw, 'height': ph, 'extent': extent},
                          'levels': levels, 'tileSize': TILE_SIZE, 'gutter': GUTTER, 'tileUrl': f'data/plans/{pid}/tiles/{{level}}/{{x}}-{{y}}.webp',
                          'detailUrl': f'data/plans/{pid}/details.json', 'orientationStatus': plan.get('orientation', {}).get('status', 'unknown')})
    expected = raster_store.expected_files(plans)
    cache_key = raster_key({'sources': [source]}) if raster_cache is not None else None
    reused = raster_cache is not None and raster_store.restore(raster_cache, cache_key, expected, out / 'plans')
    if reused:
        print(f'Raster cache hit: {len(plans)} plans, {len(expected)} raster files verified', flush=True)
    else:
        print(f'Raster cache miss; rendering {len(plans)} plans with {workers} workers', flush=True)
        render_plans(tasks, workers)
        if raster_cache is not None:
            try:
                raster_store.save(raster_cache, cache_key, expected, out / 'plans')
            except OSError as error:
                print(f'Raster cache save skipped: {error}', file=sys.stderr, flush=True)
    webp = [name for name in expected if name.endswith('.webp')]
    raster_bytes = sum((out / 'plans' / name).stat().st_size for name in webp)
    tile_count = len(webp) - len(plans)
    return plans, {'plans': len(plans), 'tiles': tile_count, 'rasterBytes': raster_bytes}


def tool_versions():
    from osgeo import gdal, osr
    import numpy
    import yaml
    return {'python': sys.version.split()[0], 'gdal': gdal.VersionInfo('--version'),
            'proj': '.'.join(str(v) for v in [osr.GetPROJVersionMajor(), osr.GetPROJVersionMinor(), osr.GetPROJVersionMicro()]),
            'numpy': numpy.__version__, 'pyyaml': yaml.__version__}


def build_report(output, counts, seconds):
    paths = [path for path in output.rglob('*') if path.is_file() and path.name != 'build-report.json']
    other_bytes = sum(path.stat().st_size for path in paths)
    report = {'profile': PROFILE, 'tools': tool_versions(), 'counts': counts, 'files': len(paths) + 1, 'bytes': other_bytes, 'buildSeconds': round(seconds, 2)}
    for _ in range(5):
        report_size = len((json.dumps(report, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode())
        if report['bytes'] == other_bytes + report_size:
            return report
        report['bytes'] = other_bytes + report_size
    raise ValueError('Build report size did not converge')


def build(lock, cache, output, *, workers=None, raster_cache=None):
    start = time.monotonic()
    cache, output = cache.resolve(), output.resolve()
    if raster_cache is not None:
        destination = raster_cache.resolve()
        require(not (destination == output or destination in output.parents or output in destination.parents), 'Raster cache and output must be separate')
        require(not (destination == cache or destination in cache.parents or cache in destination.parents), 'Raster cache and inputs must be separate')
    # Revalidate pinned bytes even when fetch used an existing cache.
    fetch(lock, cache)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='map-data-', dir=cache.parent))
    try:
        sources = {s['key']: s for s in lock['sources']}
        objects, details, counts = import_gps(cache, sources['gps'], staging)
        models = import_jktz(cache, sources['jktz'], staging, details)
        plans, raster_counts = import_plans(cache, sources['geo'], staging, details, workers=workers, raster_cache=raster_cache)
        for obj in objects:
            detail = details[obj['id']]
            obj['modelIds'], obj['planIds'] = detail['modelIds'], detail['planIds']
            write_json(staging / 'objects' / f'{obj["id"]}.json', detail)
        counts.update(raster_counts)
        counts.update({'models': len(models), 'modelFeatures': sum(m['featureCount'] for m in models)})
        catalog_sources = []
        for source in lock['sources']:
            licenses = []
            for entry in source['files']:
                if '/' not in entry['path']:
                    licenses.append({'name': entry['path'], 'url': f'https://github.com/{source["repository"]}/blob/{source["commit"]}/{entry["path"]}', 'text': source_path(cache, source, entry['path']).read_text()})
            catalog_sources.append({k: source[k] for k in ['key', 'repository', 'tag', 'commit', 'url', 'publishedAt', 'assets']} | {'licenses': licenses})
        extent = union_extent([[o['coordinate'][0], o['coordinate'][1], o['coordinate'][0], o['coordinate'][1]] for o in objects if o['coordinate']])
        catalog = {'schemaVersion': 1, 'crs': 'EPSG:2180', 'profile': PROFILE, 'generatedAt': lock['resolvedAt'], 'sources': catalog_sources, 'counts': counts, 'extent': extent, 'objects': objects, 'caves': json_read((staging / 'caves.json').read_bytes()), 'models': models, 'plans': plans}
        write_json(staging / 'catalog.json', catalog)
        write_json(staging / 'inputs.json', lock)
        shutil.copyfile(cache / 'verification.json', staging / 'input-verification.json')
        report = build_report(staging, counts, time.monotonic() - start)
        require(report['bytes'] < 850_000_000, f"Data exceeds 850 MB budget: {report['bytes']}")
        write_json(staging / 'build-report.json', report)
        if output.exists():
            shutil.rmtree(output)
        staging.replace(output)
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['resolve', 'fetch', 'build', 'cache-key'])
    parser.add_argument('--lock', type=Path, required=True)
    parser.add_argument('--cache', type=Path, default=Path('.build/inputs'))
    parser.add_argument('--output', type=Path, default=Path('public/data'))
    parser.add_argument('--workers', type=int, choices=range(1, 5))
    parser.add_argument('--raster-cache', type=Path)
    args = parser.parse_args()
    if args.command == 'resolve':
        resolve(args.lock)
    elif args.command == 'fetch':
        fetch(read_lock(args.lock), args.cache)
    elif args.command == 'cache-key':
        print(raster_key(read_lock(args.lock)))
    else:
        build(read_lock(args.lock), args.cache.resolve(), args.output.resolve(), workers=args.workers, raster_cache=args.raster_cache)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        print(f'Pipeline failed: {error}', file=sys.stderr)
        raise SystemExit(1)
