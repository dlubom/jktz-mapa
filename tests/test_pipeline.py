"""Contract tests use small generated inputs; the full build is a separate acceptance run."""
from pathlib import Path
import hashlib
import io
import json
import math
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import pipeline as p


class ModelContractTests(unittest.TestCase):
    def test_model_url_changes_only_when_geojson_changes(self):
        from osgeo import ogr, osr
        ogr.UseExceptions()
        osr.UseExceptions()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = {'key': 'jktz', 'commit': 'a' * 40, 'assets': [{'name': 'survey.zip'}]}
            template = p.source_path(root, source, 'Poligony/OTWORY.SRV.j2')
            template.parent.mkdir(parents=True)
            template.write_text('')
            reference = osr.SpatialReference()
            reference.ImportFromEPSG(32634)
            shapefile = root / 'survey.shp'
            driver = ogr.GetDriverByName('ESRI Shapefile')

            def import_survey(x, name):
                if shapefile.exists():
                    driver.DeleteDataSource(str(shapefile))
                with driver.CreateDataSource(str(shapefile)) as dataset:
                    layer = dataset.CreateLayer('survey', reference, ogr.wkbLineString25D)
                    leg = ogr.Feature(layer.GetLayerDefn())
                    leg.SetGeometry(ogr.CreateGeometryFromWkt(f'LINESTRING Z (410000 5450000 1000, {x} 5450010 1002)'))
                    layer.CreateFeature(leg)
                with zipfile.ZipFile(root / 'survey.zip', 'w') as archive:
                    for component in sorted(root.glob('survey.*')):
                        if component.suffix != '.zip':
                            archive.write(component, f'exports/caves/{component.name}')
                out = root / name / 'data'
                model, = p.import_jktz(root, source, out, {})
                content = (out.parent / model['url']).read_bytes()
                self.assertEqual('survey', model['id'])
                self.assertEqual(f'data/models/survey.{hashlib.sha256(content).hexdigest()}.geojson', model['url'])
                return model['url']

            original = import_survey(410010, 'original')
            self.assertEqual(original, import_survey(410010, 'repeat'))
            self.assertNotEqual(original, import_survey(410011, 'changed'))


class InputContractTests(unittest.TestCase):
    def test_hash_and_size_must_match_published_digest(self):
        asset = {'name': 'a.zip', 'size': 3, 'digest': 'sha256:' + p.digest(b'abc')}
        p.validate_asset(asset, b'abc')
        with self.assertRaisesRegex(ValueError, 'HASH_MISMATCH'):
            p.validate_asset(asset, b'xyz')
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_INTEGRITY'):
            p.validate_asset({**asset, 'digest': ''}, b'abc')

    def test_duplicate_json_and_unsafe_archive_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON'):
            p.json_read('{"schemaVersion":1,"schemaVersion":2}')
        for name in ('../escape', '/absolute', 'a/../escape', 'a\\b'):
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, 'w') as z:
                z.writestr(name, 'bad')
            with zipfile.ZipFile(stream) as z:
                with self.assertRaises(ValueError):
                    p.safe_archive(z)

    def test_new_run_resolves_all_sources_rerun_reads_pin_without_api(self):
        calls = []
        def fake_api(path):
            calls.append(path)
            repo = path.split('/')[2]
            if path.endswith('/releases/latest'):
                names = {'Georeferencer': ['geotiff-tatry-v2.zip'], 'gps-kataster-obiektow-tatr': ['katalog.dump', 'metadata.json'], 'Jaskiniowy-Kataster-Tatr-Zachodnich': ['JKTZ-v2.zip']}[repo]
                return {'draft': False, 'prerelease': False, 'tag_name': 'v2', 'id': 1, 'published_at': '2026-01-01', 'html_url': 'https://example.test/release', 'assets': [{'id': i, 'name': n, 'size': 3, 'digest': 'sha256:' + p.digest(b'abc'), 'browser_download_url': 'https://example.test/' + n} for i, n in enumerate(names)]}
            if '/git/ref/' in path:
                return {'object': {'sha': 'a' * 40, 'type': 'tag'}}
            if '/git/tags/' in path:
                return {'object': {'sha': 'b' * 40, 'type': 'commit'}}
            return {'truncated': False, 'tree': [{'path': 'Poligony/OTWORY.SRV.j2', 'type': 'blob', 'mode': '100644', 'sha': 'c' * 40, 'size': 1}]}
        with tempfile.TemporaryDirectory() as directory, patch.object(p, 'api', fake_api):
            path = Path(directory) / 'inputs.json'
            p.resolve(path)
            self.assertEqual(3, sum(c.endswith('/releases/latest') for c in calls))
            calls.clear()
            lock = p.read_lock(path)
            self.assertEqual('b' * 40, lock['sources'][0]['commit'])
            self.assertEqual([], calls)
            gps = next(source for source in lock['sources'] if source['key'] == 'gps')
            self.assertEqual(['katalog.dump', 'metadata.json'], [a['name'] for a in gps['assets']])
            gps['assets'][0]['name'] = 'katalog.sqlite.zip'
            legacy = Path(directory) / 'legacy.json'
            p.write_json(legacy, lock)
            with self.assertRaisesRegex(ValueError, 'GPS.*katalog.dump.*resolve'):
                p.read_lock(legacy)
            with self.assertRaisesRegex(ValueError, 'already pinned'):
                p.resolve(path)
            p.resolve(Path(directory) / 'new-run.json')
            self.assertEqual(3, sum(c.endswith('/releases/latest') for c in calls))

    def test_new_pin_refreshes_same_named_asset_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            (cache / 'katalog.dump').write_bytes(b'old')
            asset = {'id': 99, 'name': 'katalog.dump', 'size': 3, 'digest': 'sha256:' + p.digest(b'new')}
            lock = {'sources': [{'key': 'gps', 'repository': p.REPOSITORIES['gps'], 'commit': 'a' * 40, 'assets': [asset], 'files': []}]}
            def download(command, stdout, check):
                self.assertIn('repos/dlubom/gps-kataster-obiektow-tatr/releases/assets/99', command)
                stdout.write(b'new')
            with patch.object(p.subprocess, 'run', download):
                p.fetch(lock, cache)
            self.assertEqual(b'new', (cache / 'katalog.dump').read_bytes())
            with patch.object(p.subprocess, 'run', side_effect=AssertionError('Unnecessary download')):
                p.fetch(lock, cache)

    def test_axes_missing_coordinates_and_difference_are_not_accuracy(self):
        self.assertEqual([560123.0, 150345.0], p.coordinate({'x_1992': 150345.0, 'y_1992': 560123.0}))
        self.assertIsNone(p.coordinate({'x_1992': None, 'y_1992': None}))
        with self.assertRaises(ValueError):
            p.coordinate({'x_1992': math.nan, 'y_1992': 560123.0})

    def test_jktz_relationships_use_only_active_literal_calls(self):
        text = """; {{ gps_fix('Ignored:0', 'A') }}
{{ gps_fix('Cave:branch:0', 'ONE') }}
{{ gps_fix("Cave:1", "TWO", suffix='abc') }} ; comment
{{ gps_fix("KamienneMleko:0'", 'CHZ-0014') }}
{{ something_else('Other', 'NOT') }}
"""
        self.assertEqual({'Cave': [{'station': 'Cave:branch:0', 'objectId': 'ONE'}, {'station': 'Cave:1', 'objectId': 'TWO'}], 'KamienneMleko': [{'station': "KamienneMleko:0'", 'objectId': 'CHZ-0014'}]}, p.parse_relations(text))

    def test_raster_uses_all_affine_terms_and_corner_convention(self):
        gt = [100, 2, 1, 200, 1, -2]
        extent, resolution, levels = p.raster_geometry(gt, 1000, 500)
        self.assertEqual([100, -800, 2600, 1200], extent)
        self.assertAlmostEqual(math.sqrt(5), resolution)
        self.assertEqual([100, 1200], levels[0]['origin'])
        self.assertEqual(math.ceil(2500 / math.sqrt(5)), levels[0]['width'])
        self.assertEqual(3, levels[0]['columns'])
        self.assertLessEqual(levels[0]['extent'][1], extent[1])

    def test_yaml_preserves_zero_prefixed_ids_and_numeric_dimensions(self):
        data = p.read_yaml('cave:\n  source_cave_id: 001140\nimage:\n  width: 7630\n  height: 5020\ndate: 2026-10-31\n')
        self.assertEqual('001140', data['cave']['source_cave_id'])
        self.assertEqual(7630, data['image']['width'])
        self.assertEqual('2026-10-31', data['date'])
        with self.assertRaisesRegex(ValueError, 'Duplicate YAML'):
            p.read_yaml('a: 1\na: 2\n')


class GPSContractTests(unittest.TestCase):
    def test_history_uses_composite_keys_and_preserves_rejected_records(self):
        def measurement(object_id, mid, x, y, status, accuracy, notes):
            return dict(object_id=object_id, id=mid, x_1992=x, y_1992=y,
                        verification_status=status, source='PIG', horizontal_accuracy_m=accuracy, notes=notes)
        tables = {
            'objects': [dict(id='A', name_local='Otwór A', cave_id='C', membership_ordinal=2),
                        dict(id='B', name_local='Otwór B', cave_id='C', membership_ordinal=1)],
            'caves': [dict(id='C', name='Jaskinia', system_name='System', length_m=34, citations=[{'publication_id': 'PUB'}]),
                      dict(id='C-orphan', name='Bez otworu', system_name=None, notes='source note')],
            'best_measurements': [dict(object_id='A', measurement_id='m-1', mode='auto'),
                                  dict(object_id='B', measurement_id='m-1', mode='manual',
                                       computed_best_measurement_id='m-1', reason='source decision')],
            'measurements': [
                measurement('A', 'm-1', 150000, 560000, 'nieweryfikowany', None, 'original'),
                {**measurement('A', 'm-2', 150003, 560004, 'odrzucony', 7, 'rejected note'),
                 'elevation_m': 913.4, 'elevation_datum': 'Kronstadt86', 'input_srid': 2180, 'tags': ['source']},
                measurement('B', 'm-1', 160000, 570000, 'zweryfikowany', 1, 'second object'),
            ],
            'object_external_refs': [],
            'cave_external_refs': [{'cave_id': 'C', 'external_id': 'PIG-id'}],
            'relations': [],
            'attachments': [],
            'metadata': {'engine': 'PostgreSQL/PostGIS'},
            'validation_flags': [],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'katalog.dump').write_bytes(b'archive')
            p.write_json(root / 'metadata.json', {
                'metadata_schema_version': 1, 'data_schema_version': 1,
                'counts': {'objects': 2, 'caves': 2, 'measurements': 3, 'relations': 0, 'validation_errors': 0},
            })
            assets = []
            for name in ('katalog.dump', 'metadata.json'):
                data = (root / name).read_bytes()
                assets.append({'name': name, 'size': len(data), 'digest': 'sha256:' + p.digest(data)})
            source = {'tag': 'v2.0.2', 'assets': assets}
            with patch.object(p, 'read_gps_dump', return_value=tables) as read_dump:
                objects, details, counts = p.import_gps(root, source, root / 'out')
                read_dump.assert_called_once_with(b'archive')
                self.assertEqual(3, counts['sourceMeasurements'])
                caves = p.json_read((root / 'out' / 'caves.json').read_bytes())
                self.assertEqual(['B', 'A'], next(c for c in caves if c['id'] == 'C')['objectIds'])
                orphan = next(c for c in caves if c['id'] == 'C-orphan')
                self.assertEqual([], orphan['objectIds'])
                self.assertNotIn('coordinate', orphan)
                self.assertIn('source note', orphan['searchText'])
                self.assertTrue((root / 'out' / 'caves' / 'C-orphan.json').exists())
                self.assertEqual([560000, 150000], objects[0]['coordinate'])
                self.assertEqual('PIG-id', details['A']['caveExternalRefs'][0]['external_id'])
                self.assertEqual(34, details['A']['cave']['length_m'])
                self.assertEqual('PUB', details['A']['cave']['citations'][0]['publication_id'])
                rejected = details['A']['measurements'][1]
                self.assertEqual('rejected', rejected['role'])
                self.assertEqual('rejected note', rejected['notes'])
                self.assertEqual(5, rejected['differenceM'])
                self.assertEqual(7, rejected['horizontal_accuracy_m'])
                self.assertEqual(913.4, rejected['elevation_m'])
                self.assertEqual('Kronstadt86', rejected['elevation_datum'])
                self.assertEqual(['source'], rejected['tags'])
                self.assertEqual('second object', details['B']['measurements'][0]['notes'])
                self.assertIsNone(details['A']['measurements'][0]['horizontal_accuracy_m'])
                self.assertEqual('source decision', details['B']['best']['reason'])
                self.assertEqual('m-1', details['B']['best']['computed_best_measurement_id'])
                # A Best id is scoped to its object, not satisfied by another object's row.
                tables['best_measurements'][1]['measurement_id'] = 'm-2'
                with self.assertRaisesRegex(ValueError, 'Invalid Best reference: B'):
                    p.import_gps(root, source, root / 'out')
                # Never pass bytes to pg_restore after a cache replacement.
                (root / 'katalog.dump').write_bytes(b'changed')
                read_dump.reset_mock()
                with self.assertRaisesRegex(ValueError, 'ASSET_HASH_MISMATCH'):
                    p.import_gps(root, source, root / 'out')
                read_dump.assert_not_called()


class RasterContractTests(unittest.TestCase):
    def test_tile_gutter_preserves_neighbouring_pixels_and_transparent_edges(self):
        from osgeo import gdal
        import numpy as np
        ds = gdal.GetDriverByName('MEM').Create('', 520, 4, 2, gdal.GDT_Byte)
        pixels = np.tile(np.arange(520) % 255, (4, 1)).astype('uint8')
        ds.GetRasterBand(1).WriteArray(pixels)
        ds.GetRasterBand(2).Fill(255)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tile.webp'
            p.write_webp(ds, path, (511, -1, 514, 514))
            result = gdal.Open(str(path))
            self.assertEqual((514, 514, 4), (result.RasterXSize, result.RasterYSize, result.RasterCount))
            data = result.ReadAsArray()
            self.assertEqual(511 % 255, data[0, 1, 0])
            self.assertEqual(512 % 255, data[0, 1, 1])
            self.assertEqual(255, data[3, 1, 1])
            self.assertEqual(0, data[3, 0, 1])
            self.assertEqual(0, data[3, 1, 9])


if __name__ == '__main__':
    unittest.main()
