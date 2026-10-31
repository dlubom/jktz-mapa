import copy
import importlib.util
import json
from pathlib import Path
import tempfile
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
