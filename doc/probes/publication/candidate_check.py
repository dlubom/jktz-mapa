#!/usr/bin/env python3
"""Throwaway offline check of the candidate runtime; no GitHub calls or repo writes.

Archive transport and public readback are mocked, not integration evidence.
Run: python3 doc/probes/publication/candidate_check.py
"""
import base64
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('probe_review', Path(__file__).with_name('github_probe.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
archives = {k: {**v, 'asset_id': i, 'release_id': 1} for i, (k, v) in enumerate(m.CATALOG['packages'].items(), 1)}
state = {'schema': 1, 'catalog_sha256': m.digest(m.CATALOG_BYTES), 'archives': archives,
         'current': 'original', 'retired': {}, 'last': None, 'pending': None}
revision = 0
runs, written, archive_reads = {}, [], []
public = 'original'
uncertain_write = False

def api(path, method='GET', payload=None, binary=False):
    global state, revision, uncertain_write
    if path.startswith(m.STATE):
        if method == 'PUT':
            assert payload['sha'] == str(revision)
            state = json.loads(base64.b64decode(payload['content']))
            revision += 1
            written.append(copy.deepcopy(state))
            if uncertain_write:
                uncertain_write = False
                raise RuntimeError('fixture: response lost after successful CAS')
            return {}
        return {'sha': str(revision), 'content': base64.b64encode(m.encoded(state)).decode()}
    if '/actions/runs/' in path:
        suffix = path.split('/actions/runs/')[1]
        rid = int(suffix.split('/')[0])
        if '/attempts/' in suffix:
            attempt = int(suffix.split('/attempts/')[1].split('/')[0])
            return {'total_count': 1, 'jobs': [{'id': rid * 10, 'run_id': rid,
                'run_attempt': attempt, 'head_sha': 'a' * 40,
                'name': f'pages-publication-probe-{rid}-{attempt}',
                'steps': [{'name': m.STEP, 'number': m.STEP_NUMBER,
                           'status': 'completed', 'conclusion': 'success'}]}]}
        return runs[rid]
    raise AssertionError(path)

m.api = api
m.archive_bytes = lambda label, archive: (archive_reads.append(label) or b'fixture')
def check_public(label):
    assert label == public
m.public_bytes = check_public

with tempfile.TemporaryDirectory() as temp:
    output = Path(temp) / 'output'
    os.environ.update(GITHUB_ACTIONS='true', GITHUB_REPOSITORY=m.REPO,
        GITHUB_REF='refs/heads/main', GITHUB_SHA='a' * 40, RUNNER_TEMP=temp,
        GITHUB_OUTPUT=str(output), PROBE_PAUSE='false')
    def context(rid, operation, timestamp):
        os.environ.update(GITHUB_RUN_ID=str(rid), GITHUB_RUN_ATTEMPT='1', PROBE_OPERATION=operation)
        runs[rid] = {'head_sha': 'a' * 40, 'head_branch': 'main',
                    'event': 'workflow_dispatch', 'created_at': timestamp, 'run_attempt': 1}
        output.write_text('')
    def publish(rid, operation, label, timestamp):
        global public
        context(rid, operation, timestamp)
        m.workflow('prepare')
        assert output.read_text() == 'ready=true\n'
        m.workflow('pending')
        public = label
        m.workflow('confirm')
        assert state['current'] == label and state['pending'] is None
    publish(1, 'publish-A', 'A', '2026-10-31T10:00:00Z')
    context(2, 'publish-B', '2026-10-31T10:01:00Z')
    m.workflow('prepare')
    m.workflow('pending')
    public = 'B'
    context(3, 'recover', '2026-10-31T10:02:00Z')
    uncertain_write = True
    m.workflow('prepare')
    assert state['current'] == 'B'
    snapshot = m.encoded(state)
    m.workflow('prepare')
    assert m.encoded(state) == snapshot
    publish(4, 'rollback-A', 'A', '2026-10-31T10:03:00Z')
    rollback_snapshot = copy.deepcopy(state)
    context(2, 'publish-B', '2026-10-31T10:01:00Z')
    m.workflow('prepare')
    assert output.read_text() == '' and state['current'] == 'A' and state['pending'] is None
    context(6, 'publish-B', '2026-10-31T10:03:00Z')
    try:
        m.workflow('prepare')
        raise AssertionError('equal timestamps accepted')
    except RuntimeError as error:
        assert 'equal timestamps' in str(error)
    publish(5, 'restore-original', 'original', '2026-10-31T10:04:00Z')
    print(json.dumps({'lifecycle': 'passed', 'writes': len(written),
        'archive_read_labels': archive_reads, 'final_current': state['current']}, indent=2))
    state = rollback_snapshot
    state['last'] = {}
    context(2, 'publish-B', '2026-10-31T10:01:00Z')
    try:
        m.workflow('prepare')
    except (RuntimeError, KeyError, TypeError) as error:
        print(f'last={{}}: safely rejected ({type(error).__name__})')
    else:
        raise AssertionError(f'Invalid ledger accepted; stale B output={output.read_text().strip()!r}')
