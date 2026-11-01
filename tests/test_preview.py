import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import urllib.request
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('preview', ROOT / 'scripts/preview.py')
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


def identity():
    return dict(schema=1, repository='dlubom/jktz-mapa', pr=8,
                head_sha='a' * 40, base_sha='b' * 40, merge_sha='c' * 40)


def candidate():
    return dict(number=8, state='open', draft=False, mergeable=True,
                head={'sha': 'a' * 40}, base={'sha': 'b' * 40, 'ref': 'main',
                'repo': {'full_name': 'dlubom/jktz-mapa'}}, merge_commit_sha='c' * 40)


def make_site(root):
    site = root / 'site'
    files = {
        'index.html': '<html><head><link rel="stylesheet" href="./assets/map.css"></head><body><div id="app">Mapa</div><script type="module" src="./assets/map.js"></script></body></html>',
        'assets/map.js': 'console.log("map")', 'assets/map.css': 'body{margin:0}',
        'data/inputs.json': '{"sources":[]}', 'data/objects/one.json': '{}',
        'data/caves/one.json': '{}', 'data/models/one.geojson': '{}',
        'data/plans/one/preview.webp': 'preview', 'data/plans/one/details.json': '{}',
        'data/plans/one/tiles/0/0-0.webp': 'detail',
    }
    catalog = {'schemaVersion': 1, 'crs': 'EPSG:2180',
               'objects': [{'detailUrl': 'data/objects/one.json'}],
               'caves': [{'detailUrl': 'data/caves/one.json'}],
               'models': [{'url': 'data/models/one.geojson'}],
               'plans': [{'detailUrl': 'data/plans/one/details.json',
                          'preview': {'url': 'data/plans/one/preview.webp'},
                          'tileUrl': 'data/plans/one/tiles/{level}/{x}-{y}.webp',
                          'levels': [{'level': 0, 'columns': 1, 'rows': 1}]}]}
    files['data/catalog.json'] = json.dumps(catalog)
    for name, raw in files.items():
        path = site / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw)
    pins = root / 'inputs.json'
    pins.write_text(files['data/inputs.json'])
    return site, pins


class PreviewTests(unittest.TestCase):
    def test_publisher_separates_untrusted_build_from_pages_credentials(self):
        import yaml
        workflow = yaml.safe_load((ROOT / '.github/preview-repository/preview.yml').read_text())
        jobs = workflow['jobs']
        self.assertEqual(workflow['permissions'], {})
        self.assertFalse(workflow['concurrency']['cancel-in-progress'])
        self.assertEqual(jobs['build']['permissions'], {'contents': 'read'})
        self.assertNotIn('environment', jobs['build'])
        self.assertNotIn('secrets.', json.dumps(jobs['build']))
        self.assertEqual(jobs['publish']['permissions']['pages'], 'write')
        self.assertEqual(jobs['publish']['permissions']['id-token'], 'write')
        self.assertEqual(jobs['build']['steps'][0]['with']['repository'], 'dlubom/jktz-mapa')
        publish = jobs['publish']['steps']
        self.assertNotIn('repository', publish[0]['with'])
        verification = next(i for i, step in enumerate(publish) if 'preview.py verify' in step.get('run', ''))
        deployment = next(i for i, step in enumerate(publish) if 'actions/deploy-pages@' in step.get('uses', ''))
        self.assertLess(verification, deployment)
        self.assertIn('preview.py guard', publish[deployment - 1]['run'])

    def test_missing_runtime_assets_block_publish_with_consistent_checksums(self):
        for missing in ('data/catalog.json', 'assets/map.js', 'assets/map.css', 'data/objects/one.json',
                        'data/caves/one.json', 'data/models/one.geojson', 'data/plans/one/preview.webp',
                        'data/plans/one/details.json', 'data/plans/one/tiles/0/0-0.webp'):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                site, pins = make_site(root)
                bundle = root / 'bundle'
                preview.build_bundle(site, pins, bundle, identity())
                (bundle / missing).unlink()
                (bundle / 'checksums.json').write_bytes(preview.encoded(preview.inventory(bundle)))
                with self.assertRaisesRegex(RuntimeError, 'Missing|catalogue'):
                    preview.verify_bundle(bundle, identity())

    def test_small_plan_is_complete_with_preview_and_no_tile_levels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site, pins = make_site(root)
            path = site / 'data/catalog.json'
            catalog = json.loads(path.read_text())
            catalog['plans'][0]['levels'] = []
            path.write_text(json.dumps(catalog))
            (site / 'data/plans/one/tiles/0/0-0.webp').unlink()
            preview.build_bundle(site, pins, root / 'bundle', identity())
            preview.verify_bundle(root / 'bundle', identity())

    def test_older_selection_cannot_overwrite_newer_selection_even_on_rerun(self):
        runs = [{'id': 10, 'run_number': 1}, {'id': 20, 'run_number': 2}]
        with patch.object(preview, 'api', return_value={'workflow_runs': runs}), \
             patch.dict(os.environ, {'GITHUB_REPOSITORY': 'dlubom/jktz-mapa-preview',
                                     'GITHUB_REF': 'refs/heads/main', 'GITHUB_RUN_ID': '10'}):
            with self.assertRaisesRegex(RuntimeError, 'newer selection'):
                preview.guard_selection()
        with patch.object(preview, 'api', return_value={'workflow_runs': runs}), \
             patch.dict(os.environ, {'GITHUB_REPOSITORY': 'dlubom/jktz-mapa-preview',
                                     'GITHUB_REF': 'refs/heads/main', 'GITHUB_RUN_ID': '20'}):
            preview.guard_selection()

    def test_complete_flat_bundle_and_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site, pins = make_site(root)
            (site / 'data/plans/detail.webp').write_bytes(b'webp detail')
            result = preview.build_bundle(site, pins, root / 'bundle', identity())
            self.assertEqual(result['pr'], 8)
            bundle = root / 'bundle'
            self.assertEqual((bundle / 'data/plans/detail.webp').read_bytes(), b'webp detail')
            self.assertTrue((bundle / 'serve.py').is_file())
            self.assertTrue((bundle / 'URUCHOMIENIE.txt').is_file())
            self.assertEqual((bundle / 'inputs.json').read_bytes(), pins.read_bytes())
            self.assertIn('PR #8', (bundle / 'index.html').read_text())
            preview.verify_bundle(bundle, identity())
            (bundle / 'data/plans/detail.webp').write_bytes(b'damaged')
            with self.assertRaisesRegex(RuntimeError, 'checksum'):
                preview.verify_bundle(bundle, identity())

    def test_bundle_rejects_symlinks_and_nested_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site = root / 'site'
            site.mkdir()
            (site / 'index.html').write_text('<body>Mapa</body>')
            pins = root / 'inputs.json'
            pins.write_text('{}')
            with self.assertRaisesRegex(RuntimeError, 'outside'):
                preview.build_bundle(site, pins, site / 'out', identity())
            (site / 'secret').symlink_to(pins)
            with self.assertRaisesRegex(RuntimeError, 'Symlink'):
                preview.build_bundle(site, pins, root / 'out', identity())

    def test_inventory_rejects_unsafe_names_extra_files_and_wrong_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_site(root)
            bundle = root / 'bundle'
            preview.build_bundle(root / 'site', root / 'inputs.json', bundle, identity())
            wrong = identity() | {'head_sha': 'd' * 40}
            with self.assertRaisesRegex(RuntimeError, 'identity'):
                preview.verify_bundle(bundle, wrong)
            (bundle / 'unexpected').write_text('extra')
            with self.assertRaisesRegex(RuntimeError, 'inventory'):
                preview.verify_bundle(bundle, identity())
            (bundle / 'unexpected').unlink()
            checksums = json.loads((bundle / 'checksums.json').read_text())
            checksums['../escape'] = 'a' * 64
            (bundle / 'checksums.json').write_text(json.dumps(checksums))
            with self.assertRaisesRegex(RuntimeError, 'Unsafe'):
                preview.verify_bundle(bundle, identity())

    def test_candidate_requires_open_pr_to_main_and_exact_merge_parents(self):
        pr = candidate()
        commit = {'sha': 'c' * 40, 'parents': [{'sha': 'b' * 40}, {'sha': 'a' * 40}]}
        self.assertEqual(preview.candidate_identity(pr, commit), identity())
        for key, value in [('state', 'closed'), ('mergeable', False), ('mergeable', None), ('merge_commit_sha', None)]:
            invalid = copy.deepcopy(pr)
            invalid[key] = value
            with self.assertRaises(RuntimeError):
                preview.candidate_identity(invalid, commit)
        invalid = copy.deepcopy(pr)
        invalid['base']['ref'] = 'other'
        with self.assertRaises(RuntimeError):
            preview.candidate_identity(invalid, commit)
        with self.assertRaisesRegex(RuntimeError, 'parents'):
            preview.candidate_identity(pr, commit | {'parents': [{'sha': 'd' * 40}, {'sha': 'a' * 40}]})

    def test_downloaded_launcher_serves_complete_bundle_without_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'index.html').write_text('<h1>Mapa</h1>')
            (root / 'tile.webp').write_bytes(b'detail')
            import sys
            process = subprocess.Popen([sys.executable, str(ROOT / 'scripts/preview-server.py'), '--directory', str(root), '--port', '0'], stdout=subprocess.PIPE, text=True)
            try:
                url = process.stdout.readline().strip()
                self.assertTrue(url.startswith('http://127.0.0.1:'))
                self.assertEqual(urllib.request.urlopen(url, timeout=5).read(), b'<h1>Mapa</h1>')
                response = urllib.request.urlopen(url + 'tile.webp', timeout=5)
                self.assertEqual(response.headers['Content-Type'], 'image/webp')
                self.assertEqual(response.read(), b'detail')
            finally:
                process.terminate()
                process.wait(timeout=5)
                process.stdout.close()


if __name__ == '__main__':
    unittest.main()
