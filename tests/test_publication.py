import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import tarfile
import subprocess
import zipfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('publication', Path(__file__).parents[1] / 'scripts/publication.py')
pub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pub)


def operation(number, day):
    return {'run_id': number, 'run_attempt': 1, 'created_at': f'2026-10-{day:02d}T12:00:00Z',
            'head_sha': 'a' * 40, 'job_name': f'publish-{number}-1', 'step_name': 'Publish Pages'}


def archive(number):
    return {'release_id': number, 'asset_id': number, 'bytes': 10, 'sha256': 'a' * 64,
            'manifest_sha256': 'b' * 64, 'files': {'index.html': 'c' * 64}}


def state():
    return {'schema': 1, 'current': 'pages-A', 'archives': {'pages-A': archive(1)},
            'retired': {}, 'last': None, 'pending': None}


class PublicationTests(unittest.TestCase):
    def test_new_run_resolves_but_rerun_never_resolves_latest(self):
        calls = []
        resolver = lambda: calls.append('latest') or {'version': len(calls)}
        first = pub.choose_inputs(1, None, resolver)
        self.assertEqual(pub.choose_inputs(2, first, resolver), first)
        self.assertEqual(pub.choose_inputs(1, None, resolver), {'version': 2})
        with self.assertRaisesRegex(RuntimeError, 'nowe Run'):
            pub.choose_inputs(2, None, resolver)
        self.assertEqual(calls, ['latest', 'latest'])

    def test_inputs_readback_downloads_zip_with_json_accept_header(self):
        pins = b'{"schemaVersion":1,"sources":[]}\n'
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('inputs.json', pins)
        zipped = buffer.getvalue()
        artifact = {'id': 123, 'expired': False, 'digest': 'sha256:' + pub.digest(zipped)}
        requests = []
        def github(args, **kwargs):
            path, accept = args[4], args[6]
            requests.append((path, accept))
            if path.endswith('/123/zip'):
                if accept != 'Accept: application/vnd.github+json':
                    return subprocess.CompletedProcess(args, 1, b'', b'Unsupported Accept header (HTTP 415)')
                return subprocess.CompletedProcess(args, 0, zipped, b'')
            return subprocess.CompletedProcess(args, 0, pub.encoded({'artifacts': [artifact]}), b'')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'inputs.json').write_bytes(pins)
            output = root / 'output.txt'
            with patch.object(pub, 'BUILD', root), patch.object(pub.subprocess, 'run', side_effect=github), \
                 patch.dict(os.environ, {'GITHUB_RUN_ID': '456', 'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_OUTPUT': str(output)}):
                pub.inputs_phase(readback=True)
            self.assertEqual((root / 'inputs.json').read_bytes(), pins)
            self.assertEqual(output.read_text(), 'upload=false\n')
            self.assertEqual(requests[-1], ('repos/dlubom/jktz-mapa/actions/artifacts/123/zip', 'Accept: application/vnd.github+json'))

    def test_release_asset_download_keeps_octet_stream_header(self):
        raw = b'archive bytes'
        asset = {'id': 123, 'size': len(raw), 'digest': 'sha256:' + pub.digest(raw)}
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(pub.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, raw, b'')) as github:
            target = Path(temp) / 'release.tar'
            pub.download_asset(asset, target)
            self.assertEqual(target.read_bytes(), raw)
            self.assertIn('Accept: application/octet-stream', github.call_args.args[0])

    def test_prepare_requires_existing_ledger_without_bootstrap(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(pub, 'ROOT', Path(temp)), \
             patch.object(pub, 'operation', return_value=operation(2, 2)), \
             patch.object(pub, 'api', return_value=None) as api, \
             patch.object(pub, 'save_state') as save:
            with self.assertRaisesRegex(RuntimeError, 'Missing pages-state/state.json'):
                pub.deploy_phase('prepare', 'pages-B')
            api.assert_called_once_with(f'{pub.STATE_PATH}?ref={pub.BRANCH}', missing_ok=True)
            save.assert_not_called()

    def test_prepare_rollback_uses_existing_ledger_without_documentation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = root / 'original.tar'
            content = b'original static page'
            with tarfile.open(original, 'w') as tar:
                member = tarfile.TarInfo('index.html')
                member.size = len(content)
                tar.addfile(member, io.BytesIO(content))
            legacy = {'release_id': 2, 'asset_id': 3, 'bytes': original.stat().st_size,
                      'sha256': pub.digest(original.read_bytes()), 'manifest_sha256': None,
                      'files': {'index.html': pub.digest(content)}}
            data = state()
            data['archives']['probe-original'] = legacy
            data['retired']['probe-original'] = '2026-10-17T12:00:00Z'
            with patch.object(pub, 'ROOT', root), patch.object(pub, 'BUILD', root / 'build'), \
                 patch.object(pub, 'operation', return_value=operation(2, 2)), \
                 patch.object(pub, 'read_state', return_value=(data, 'ledger-sha')), \
                 patch.object(pub, 'api', side_effect=AssertionError('Unexpected bootstrap API request')), \
                 patch.object(pub, 'verify_remote_archive', return_value=original) as download, \
                 patch.object(pub, 'fetch_archive') as fetch, patch.object(pub, 'output') as output:
                pub.deploy_phase('prepare', 'probe-original')
            self.assertEqual((root / 'build/publish-site/index.html').read_bytes(), content)
            prepared = json.loads((root / 'build/prepared.json').read_bytes())
            self.assertEqual(prepared['sha'], 'ledger-sha')
            self.assertEqual(prepared['state'], data)
            self.assertEqual(prepared['transition']['pending']['to'], 'probe-original')
            download.assert_any_call(legacy, 'target.tar.gz')
            fetch.assert_not_called()
            output.assert_called_once_with('ready', 'true')

    def test_retention_starts_at_replacement_not_build(self):
        data = pub.prepare_transition(state(), operation(2, 2), 'pages-B', archive(2))
        self.assertEqual(data['retired'], {})  # a failed deploy does not start retirement
        with self.assertRaisesRegex(RuntimeError, 'pending'):
            pub.prepare_transition(data, operation(3, 3), 'pages-C', archive(3))
        self.assertEqual(pub.cleanup_candidates(data, '2027-01-01T00:00:00Z'), [])
        data = pub.complete_transition(data, '2027-01-01T00:00:00Z')
        self.assertEqual(data['retired']['pages-A'], '2027-01-16T00:00:00+00:00')
        self.assertEqual(pub.cleanup_candidates(data, '2027-01-15T23:59:59Z'), [])
        self.assertEqual(pub.cleanup_candidates(data, '2027-01-16T00:00:00Z'), ['pages-A'])

    def test_rollback_renews_retention_and_stale_run_cannot_replace_it(self):
        data = pub.complete_transition(pub.prepare_transition(state(), operation(2, 2), 'pages-B', archive(2)), '2026-10-02T13:00:00Z')
        data = pub.complete_transition(pub.prepare_transition(data, operation(4, 4), 'pages-A', archive(1)), '2026-10-04T13:00:00Z')
        self.assertNotIn('pages-A', data['retired'])
        self.assertIsNone(pub.prepare_transition(data, operation(2, 2), 'pages-B', archive(2)))
        self.assertIsNone(pub.prepare_transition(data, operation(4, 4), 'pages-A', archive(1)))
        with self.assertRaisesRegex(RuntimeError, 'equal'):
            pub.prepare_transition(data, operation(5, 4), 'pages-B', archive(2))
        data = pub.complete_transition(pub.prepare_transition(data, operation(6, 6), 'pages-B', archive(2)), '2026-10-06T13:00:00Z')
        self.assertEqual(data['retired']['pages-A'], '2026-10-21T13:00:00+00:00')

    def test_current_package_republish_does_not_retire_it(self):
        data = pub.complete_transition(pub.prepare_transition(state(), operation(2, 2), 'pages-A', archive(1)), '2026-10-02T13:00:00Z')
        self.assertEqual(data['retired'], {})
        self.assertEqual(pub.cleanup_candidates(data, '2027-01-01T00:00:00Z'), [])

    def test_malformed_state_blocks_changes(self):
        for key, value in [('retired', []), ('pending', {}), ('current', None), ('archives', {})]:
            data = state()
            data[key] = value
            with self.assertRaises(RuntimeError):
                pub.prepare_transition(data, operation(2, 2), 'pages-B', archive(2))
            with self.assertRaises(RuntimeError):
                pub.cleanup_candidates(data, '2027-01-01T00:00:00Z')

    def test_exact_step_requires_matching_attempt_job_and_success(self):
        op = operation(2, 2)
        op.update(job_id=20, step_number=6)
        job = {'id': 20, 'name': op['job_name'], 'run_id': 2, 'run_attempt': 1,
               'head_sha': op['head_sha'], 'conclusion': 'cancelled',
               'steps': [{'name': 'Publish Pages', 'number': 6, 'status': 'completed', 'conclusion': 'success'}]}
        run = {'head_sha': op['head_sha'], 'created_at': op['created_at']}
        def fake_api(path):
            return {'jobs': [job], 'total_count': 1} if '/jobs?' in path else run
        with patch.object(pub, 'api', side_effect=fake_api):
            # The whole job may be cancelled after its successful deployment step.
            self.assertEqual(pub.exact_step(op, True), {'job_id': 20, 'step_number': 6})
            for field, wrong in [('run_attempt', 2), ('id', 21), ('head_sha', 'b' * 40)]:
                original = job[field]
                job[field] = wrong
                with self.assertRaises(RuntimeError):
                    pub.exact_step(op, True)
                job[field] = original
            job['steps'][0]['conclusion'] = 'cancelled'
            with self.assertRaisesRegex(RuntimeError, 'unknown'):
                pub.exact_step(op, True)

    def test_lost_cas_response_is_read_back_without_second_write(self):
        data = state()
        with patch.object(pub, 'api', side_effect=pub.ApiError('response lost')) as write, \
             patch.object(pub, 'read_state', return_value=(data, 'new-sha')):
            pub.save_state(data, 'old-sha')
            self.assertEqual(write.call_count, 1)
        with patch.object(pub, 'api', side_effect=pub.ApiError('conflict')) as write, \
             patch.object(pub, 'read_state', return_value=({'different': True}, 'other-sha')):
            with self.assertRaisesRegex(RuntimeError, 'CAS/readback'):
                pub.save_state(data, 'old-sha')
            self.assertEqual(write.call_count, 1)

    def test_large_inventory_is_not_copied_into_ledger(self):
        record = archive(2)
        record.pop('files')
        record.update(metadata_asset_id=22, metadata_sha256='d' * 64,
                      public_files={'publication.json': 'e' * 64})
        result = pub.prepare_transition(state(), operation(2, 2), 'pages-B', record)
        pub.validate_state(result)
        self.assertNotIn('files', result['archives']['pages-B'])

    def test_archive_is_complete_reproducible_and_checked_before_materialization(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            site = root / 'dist'
            site.mkdir()
            (site / 'index.html').write_text('<h1>Mapa</h1>')
            (site / '.nojekyll').write_text('')
            inputs = root / 'inputs.json'
            inputs.write_text('{"sources":[]}')
            first = pub.build_package(site, inputs, root / 'one', 'pages-123', 'a' * 40)
            second = pub.build_package(site, inputs, root / 'two', 'pages-123', 'a' * 40)
            self.assertEqual(first, second)
            self.assertEqual((root / 'one/site.tar.gz').read_bytes(), (root / 'two/site.tar.gz').read_bytes())
            pub.verify_package(root / 'one/site.tar.gz', first, root / 'restored')
            self.assertEqual((root / 'restored/index.html').read_bytes(), (site / 'index.html').read_bytes())
            self.assertEqual(json.loads((root / 'restored/publication.json').read_text())['package_id'], 'pages-123')
            damaged = copy.deepcopy(first)
            damaged['files']['index.html'] = '0' * 64
            with self.assertRaises(RuntimeError):
                pub.verify_package(root / 'one/site.tar.gz', damaged, root / 'bad')
            self.assertFalse((root / 'bad').exists())


if __name__ == '__main__':
    unittest.main()
