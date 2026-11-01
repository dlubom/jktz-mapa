"""Real GDAL contract tests for deterministic workers and optional raster cache."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import pipeline as p


def fixture(root):
    from osgeo import gdal, osr
    import numpy as np
    gdal.UseExceptions()
    crs = osr.SpatialReference()
    crs.ImportFromEPSG(2180)
    source = {'key': 'geo', 'commit': 'a' * 40, 'repository': p.REPOSITORIES['geo'],
              'assets': [{'name': 'geo.zip'}], 'files': []}
    manifest = {'schema_version': 1, 'content_version': 't10-content-v1', 'status': 'complete',
                'release': {'version': 't11-v2', 'files': []},
                'geometry': {'model': 't06-local-similarity-v1'}, 'plans': []}
    with zipfile.ZipFile(root / 'geo.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        # Keep the small plan first: scheduling must not reorder the catalogue.
        for pid, width, height in [('small', 12, 9), ('rotated', 680, 530)]:
            tif = root / f'{pid}.tif'
            ds = gdal.GetDriverByName('GTiff').Create(str(tif), width, height, 1, gdal.GDT_Byte,
                                                     options=['NBITS=1', 'COMPRESS=DEFLATE'])
            ds.SetSpatialRef(crs)
            ds.SetGeoTransform([560000, .9, .2, 150000, .15, -.9])
            ds.GetRasterBand(1).WriteArray((np.indices((height, width)).sum(axis=0) % 2).astype('uint8'))
            gt = list(ds.GetGeoTransform())
            ds = None
            meta = f'cave:\n  name: {pid}\ncoordinates:\n  gps_kataster_object_id: A\n'.encode()
            local = p.source_path(root, source, f'data/caves/{pid}/meta.yaml')
            local.parent.mkdir(parents=True)
            local.write_bytes(meta)
            plan = {'dir_id': pid, 'acceptance': {'size': [width, height], 'geotransform': gt, 'crs': 'EPSG:2180'},
                    'inputs': {'meta.yaml': p.digest(meta)}, 'measurement': {'object_id': 'A', 'name_local': pid}}
            manifest['plans'].append(plan)
            for output, raw in [('image_georef.tif', tif.read_bytes()), ('computed.json', b'{"value":1}\n'), ('image.tfw', b'1\n0\n0\n-1\n0\n0\n')]:
                name = f'{pid}/{output}'
                archive.writestr(name, raw)
                manifest['release']['files'].append({'plan_id': pid, 'output': output, 'archive_path': name, 'sha256': p.digest(raw)})
        archive.writestr('manifest.json', json.dumps(manifest))
    source['assets'][0].update(size=(root / 'geo.zip').stat().st_size,
                               digest='sha256:' + p.digest((root / 'geo.zip').read_bytes()))
    return source


def inventory(root):
    return {str(f.relative_to(root)): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in root.rglob('*') if f.is_file()}


class RasterWorkersTests(unittest.TestCase):
    def test_empty_raster_set_can_be_cached_without_creating_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p.raster_store.save(root / 'cache', 'empty', set(), root / 'no-source-files')
            self.assertTrue(p.raster_store.restore(root / 'cache', 'empty', set(), root / 'output'))
            self.assertFalse((root / 'output').exists())

    def test_processes_preserve_all_bytes_metadata_and_manifest_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = fixture(root)
            outputs = []
            for workers in (1, 2):
                details = {'A': {'planIds': []}}
                out = root / str(workers)
                result = p.import_plans(root, source, out, details, workers=workers)
                outputs.append((result, details, inventory(out)))
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[1][1]['A']['planIds'], ['small', 'rotated'])
            self.assertEqual([plan['id'] for plan in outputs[1][0][0]], ['small', 'rotated'])
            self.assertEqual(outputs[1][0][0][0]['levels'], [])
            self.assertTrue(any('/tiles/' in name for name in outputs[1][2]))

    def test_warm_cache_skips_render_and_rebuilds_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = fixture(root)
            cache = root / 'rasters'
            first = p.import_plans(root, source, root / 'cold', {'A': {'planIds': []}}, workers=2, raster_cache=cache)
            details = {'A': {'planIds': []}}
            with patch.object(p, 'render_plan', side_effect=AssertionError('warm cache rendered again')):
                second = p.import_plans(root, source, root / 'warm', details, workers=1, raster_cache=cache)
            self.assertEqual(first, second)
            self.assertEqual(inventory(root / 'cold'), inventory(root / 'warm'))
            self.assertEqual(details['A']['planIds'], ['small', 'rotated'])

    def test_bad_cache_is_regenerated_without_copying_unsafe_entries(self):
        for fault in ('missing', 'corrupt', 'extra', 'symlink', 'manifest', 'deep-manifest'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = fixture(root)
                cache = root / 'rasters'
                p.import_plans(root, source, root / 'original', {}, workers=1, raster_cache=cache)
                webp = next(cache.rglob('preview.webp'))
                if fault == 'missing':
                    webp.unlink()
                elif fault == 'corrupt':
                    webp.write_bytes(b'bad')
                elif fault == 'extra':
                    (cache / 'extra.webp').write_bytes(b'bad')
                elif fault == 'symlink':
                    webp.unlink()
                    webp.symlink_to(root / 'geo.zip')
                elif fault == 'manifest':
                    (cache / 'manifest.json').write_text('{}')
                else:
                    (cache / 'manifest.json').write_text('[' * 10000 + '0' + ']' * 10000)
                p.import_plans(root, source, root / 'rebuilt', {}, workers=1, raster_cache=cache)
                self.assertEqual(inventory(root / 'original'), inventory(root / 'rebuilt'))
                self.assertFalse((root / 'rebuilt/extra.webp').exists())

    def test_key_ignores_run_time_and_gps_but_invalidates_geo_and_renderer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = fixture(root)
            lock = {'resolvedAt': 'first', 'sources': [source, {'key': 'gps', 'commit': 'b' * 40}]}
            first = p.raster_key(lock)
            other = copy.deepcopy(lock)
            other['resolvedAt'] = 'second'
            other['sources'][1]['commit'] = 'c' * 40
            self.assertEqual(first, p.raster_key(other))
            other['sources'][0]['assets'][0]['digest'] = 'sha256:' + 'd' * 64
            self.assertNotEqual(first, p.raster_key(other))
            with patch.object(p, 'PROFILE', 'new-rendering-profile'):
                self.assertNotEqual(first, p.raster_key(lock))

    def test_key_invalidates_changed_code_and_native_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = fixture(root)
            renderer = root / 'renderer.py'
            renderer.write_text('first renderer')
            first = p.raster_store.key(source, 'profile', renderer)
            renderer.write_text('changed renderer')
            self.assertNotEqual(first, p.raster_store.key(source, 'profile', renderer))
            renderer.write_text('first renderer')
            with patch.object(p.raster_store, 'environment', return_value={'native': 'different encoder'}):
                self.assertNotEqual(first, p.raster_store.key(source, 'profile', renderer))

    def test_worker_failure_is_reported_and_existing_catalogue_survives(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / 'existing'
            out.mkdir()
            (out / 'catalog.json').write_text('previous complete catalogue')
            with patch.object(p, 'fetch'), patch.object(p, 'import_gps', return_value=([], {}, {})), \
                 patch.object(p, 'import_jktz', return_value=[]), \
                 patch.object(p, 'import_plans', side_effect=RuntimeError('worker failed')):
                with self.assertRaisesRegex(RuntimeError, 'worker failed'):
                    p.build({'sources': [{'key': key} for key in ('gps', 'jktz', 'geo')]}, root / 'inputs', out, workers=2)
            self.assertEqual((out / 'catalog.json').read_text(), 'previous complete catalogue')
            self.assertEqual(list(root.glob('map-data-*')), [])

    def test_gdal_configuration_changes_cache_identity_and_worker_output(self):
        from osgeo import gdal
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = fixture(root)
            cache = root / 'rasters'
            lock = {'sources': [source]}
            first = p.raster_key(lock)
            p.import_plans(root, source, root / 'default', {}, workers=1, raster_cache=cache)
            with patch.dict(os.environ, {'GDAL_PAM_ENABLED': 'NO'}):
                self.assertNotEqual(first, p.raster_key(lock))
                for workers in (1, 2):
                    p.import_plans(root, source, root / f'no-pam-{workers}', {}, workers=workers,
                                   raster_cache=root / f'empty-cache-{workers}')
                self.assertEqual(inventory(root / 'no-pam-1'), inventory(root / 'no-pam-2'))
                self.assertFalse(list((root / 'no-pam-1').rglob('*.aux.xml')))
            # Programmatic TLS is not inherited through os.environ by spawn.
            previous = gdal.GetThreadLocalConfigOption('GDAL_PAM_ENABLED')
            try:
                gdal.SetThreadLocalConfigOption('GDAL_PAM_ENABLED', 'NO')
                p.import_plans(root, source, root / 'thread-local', {}, workers=2)
                self.assertEqual(inventory(root / 'no-pam-1'), inventory(root / 'thread-local'))
            finally:
                gdal.SetThreadLocalConfigOption('GDAL_PAM_ENABLED', previous)

    def test_cache_cannot_replace_inputs_reached_through_a_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = root / 'inputs'
            inputs.mkdir()
            (inputs / 'source').write_bytes(b'preserve source')
            alias = root / 'input-alias'
            alias.symlink_to(inputs, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'separate'):
                p.build({'sources': []}, alias, root / 'out', raster_cache=inputs)
            self.assertEqual((inputs / 'source').read_bytes(), b'preserve source')
            self.assertEqual([path.name for path in inputs.iterdir()], ['source'])


if __name__ == '__main__':
    unittest.main()
