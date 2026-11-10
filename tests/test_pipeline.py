"""Contract tests use small generated inputs; the full build is a separate acceptance run."""
from pathlib import Path
import errno
import io
import json
import math
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import pipeline as p


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
                names = {'Georeferencer': ['geotiff-tatry-v2.zip'], 'gps-kataster-obiektow-tatr': ['katalog.sqlite.zip', 'metadata.json'], 'Jaskiniowy-Kataster-Tatr-Zachodnich': ['JKTZ-v2.zip']}[repo]
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
            with self.assertRaisesRegex(ValueError, 'already pinned'):
                p.resolve(path)
            p.resolve(Path(directory) / 'new-run.json')
            self.assertEqual(3, sum(c.endswith('/releases/latest') for c in calls))

    def test_new_pin_refreshes_same_named_asset_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            (cache / 'katalog.sqlite.zip').write_bytes(b'old')
            asset = {'id': 99, 'name': 'katalog.sqlite.zip', 'size': 3, 'digest': 'sha256:' + p.digest(b'new')}
            lock = {'sources': [{'key': 'gps', 'repository': p.REPOSITORIES['gps'], 'commit': 'a' * 40, 'assets': [asset], 'files': []}]}
            def download(command, stdout, check):
                self.assertIn('repos/dlubom/gps-kataster-obiektow-tatr/releases/assets/99', command)
                stdout.write(b'new')
            with patch.object(p.subprocess, 'run', download):
                p.fetch(lock, cache)
            self.assertEqual(b'new', (cache / 'katalog.sqlite.zip').read_bytes())
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
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / 'source.sqlite'
            con = sqlite3.connect(db)
            con.executescript("""
                create table metadata (key text, value text);
                insert into metadata values ('schema_version','1');
                create table caves (id text, name text, system_name text, notes text);
                insert into caves values ('C','Jaskinia','System','alias'),('C-orphan','Bez otworu',null,'source note');
                create table objects (id text,name_local text,cave_id text,best_measurement_id text,notes text);
                insert into objects values ('A','Otwór A','C','m-1',null),('B','Otwór B','C','m-1',null);
                create table best_measurements (object_id text,measurement_id text);
                insert into best_measurements values ('A','m-1'),('B','m-1');
                create table measurements (object_id text,id text,x_1992 real,y_1992 real,verification_status text,source text,horizontal_accuracy_m real,notes text);
                insert into measurements values ('A','m-1',150000,560000,'nieweryfikowany','PIG',null,'original'),('A','m-2',150003,560004,'odrzucony','GPS',7,'rejected note'),('B','m-1',160000,570000,'zweryfikowany','GPS',1,'second object');
                create table object_external_refs (object_id text,external_id text);
                create table cave_external_refs (cave_id text,external_id text);
                create table relations (from_object_id text,to_object_id text);
                create table attachments (object_id text);
                create table validation_flags (code text);
            """)
            con.commit()
            con.close()
            with zipfile.ZipFile(root / 'katalog.sqlite.zip', 'w') as archive:
                archive.write(db, 'katalog.sqlite')
            p.write_json(root / 'metadata.json', {'metadata_schema_version': 1, 'data_schema_version': 1})
            objects, details, counts = p.import_gps(root, {}, root / 'out')
            self.assertEqual(3, counts['measurements'])
            caves = p.json_read((root / 'out' / 'caves.json').read_bytes())
            orphan = next(c for c in caves if c['id'] == 'C-orphan')
            self.assertEqual([], orphan['objectIds'])
            self.assertNotIn('coordinate', orphan)
            self.assertIn('source note', orphan['searchText'])
            self.assertTrue((root / 'out' / 'caves' / 'C-orphan.json').exists())
            self.assertEqual([560000,150000], objects[0]['coordinate'])
            rejected = details['A']['measurements'][1]
            self.assertEqual('rejected', rejected['role'])
            self.assertEqual('rejected note', rejected['notes'])
            self.assertEqual(5, rejected['differenceM'])
            self.assertEqual(7, rejected['horizontal_accuracy_m'])
            self.assertEqual('second object', details['B']['measurements'][0]['notes'])
            self.assertIsNone(details['A']['measurements'][0]['horizontal_accuracy_m'])
            # A Best id is scoped to its object, not satisfied by another object's row.
            con = sqlite3.connect(db)
            con.execute("update best_measurements set measurement_id='m-2' where object_id='B'")
            con.commit()
            con.close()
            with zipfile.ZipFile(root / 'katalog.sqlite.zip', 'w') as archive:
                archive.write(db, 'katalog.sqlite')
            with self.assertRaisesRegex(ValueError, 'Invalid Best reference: B'):
                p.import_gps(root, {}, root / 'out')


class BuildPublicationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.cache = self.root / 'inputs'
        self.output = self.root / 'public' / 'data'
        self.lock = {'resolvedAt': '2026-01-01', 'sources': [
            {'key': key, 'repository': repository, 'tag': 'v1', 'commit': 'a' * 40,
             'url': 'https://example.test/release', 'publishedAt': '2026-01-01',
             'assets': [], 'files': []}
            for key, repository in p.REPOSITORIES.items()
        ]}

        # Only source conversion is replaced: fetch, catalog/report writing,
        # directory publication and cleanup all use the production code.
        def import_gps(cache, source, output):
            p.write_json(output / 'caves.json', [])
            return ([{'id': 'A', 'coordinate': [560000, 150000]}],
                    {'A': {'modelIds': [], 'planIds': []}}, {'objects': 1})
        for name, replacement in (
            ('import_gps', import_gps),
            ('import_jktz', lambda *args: []),
            ('import_plans', lambda *args, **kwargs: ([], {'plans': 0, 'tiles': 0, 'rasterBytes': 0})),
        ):
            patcher = patch.object(p, name, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_overlapping_input_and_output_paths_are_rejected_before_mutation(self):
        for cache, output in (
            (self.root / 'same', self.root / 'same'),
            (self.root / 'inside-input', self.root / 'inside-input' / 'output'),
            (self.root / 'inside-output' / 'input', self.root / 'inside-output'),
        ):
            with self.subTest(cache=cache, output=output):
                cache.mkdir(parents=True)
                (cache / 'source.txt').write_text('original input')
                with self.assertRaisesRegex(ValueError, 'Inputs and output must be separate'):
                    p.build(self.lock, cache, output)
                self.assertEqual('original input', (cache / 'source.txt').read_text())
                self.assertFalse((cache / 'verification.json').exists())

    def test_symlink_alias_of_input_is_rejected_before_mutation(self):
        self.cache.mkdir()
        alias = self.root / 'alias'
        alias.symlink_to(self.cache, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Inputs and output must be separate'):
            p.build(self.lock, self.cache, alias / 'data')
        self.assertEqual([], list(self.cache.iterdir()))

    def test_existing_output_file_is_rejected_before_mutation(self):
        self.output.parent.mkdir(parents=True)
        self.output.write_text('unrelated file')
        with self.assertRaisesRegex(ValueError, 'Output must be a directory'):
            p.build(self.lock, self.cache, self.output)
        self.assertEqual('unrelated file', self.output.read_text())
        self.assertFalse(self.cache.exists())

    def test_failed_promotion_preserves_previous_complete_output(self):
        self.output.mkdir(parents=True)
        (self.output / 'previous.txt').write_text('previous successful build')
        replace = Path.replace

        def fail_new_output(path, target):
            if (path / 'catalog.json').is_file() and Path(target) == self.output:
                raise OSError(errno.EACCES, 'simulated publication failure')
            return replace(path, target)

        with patch.object(Path, 'replace', fail_new_output):
            with self.assertRaisesRegex(OSError, 'simulated publication failure'):
                p.build(self.lock, self.cache, self.output)
        self.assertEqual(['previous.txt'], sorted(path.name for path in self.output.iterdir()))
        self.assertEqual('previous successful build', (self.output / 'previous.txt').read_text())
        self.assertEqual([self.output], list(self.output.parent.iterdir()))

    def test_staging_uses_destination_filesystem_and_replaces_old_output(self):
        self.output.mkdir(parents=True)
        (self.output / 'obsolete.txt').write_text('old')
        replace = Path.replace

        def require_destination_filesystem(path, target):
            if (path / 'catalog.json').is_file() and path.parent != Path(target).parent:
                raise OSError(errno.EXDEV, 'simulated separate cache filesystem')
            return replace(path, target)

        with patch.object(Path, 'replace', require_destination_filesystem):
            p.build(self.lock, self.cache, self.output)
        self.assertEqual('A', p.json_read((self.output / 'catalog.json').read_bytes())['objects'][0]['id'])
        self.assertFalse((self.output / 'obsolete.txt').exists())
        self.assertEqual([self.output], list(self.output.parent.iterdir()))
        self.assertTrue((self.cache / 'verification.json').is_file())

    def test_failed_restore_keeps_previous_output_for_manual_recovery(self):
        self.output.mkdir(parents=True)
        (self.output / 'previous.txt').write_text('previous successful build')
        replace = Path.replace

        def fail_publication_and_restore(path, target):
            if Path(target) == self.output:
                raise OSError(errno.EACCES, 'simulated publication failure')
            return replace(path, target)

        with patch.object(Path, 'replace', fail_publication_and_restore):
            with self.assertRaises(OSError):
                p.build(self.lock, self.cache, self.output)
        retained = list(self.output.parent.rglob('previous.txt'))
        self.assertEqual(1, len(retained))
        self.assertEqual('previous successful build', retained[0].read_text())


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
