#!/usr/bin/env python3
"""Pages archives and the small publication ledger. Remote writes run only in Actions.

An unknown deploy remains pending for manual diagnosis. Publication requires
the existing pages-state ledger; this helper never initialises a new ledger.
"""
import argparse
import base64
import copy
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
import time
from datetime import datetime, timedelta, timezone
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REPO = 'dlubom/jktz-mapa'
BRANCH = 'pages-state'
STATE_PATH = f'repos/{REPO}/contents/state.json'
PUBLIC = 'https://dlubom.github.io/jktz-mapa/'
BUILD = ROOT / '.build'
STEP = 'Publish Pages'


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + '\n').encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def timestamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None, 'Timestamp needs timezone')
    return result


def choose_inputs(attempt, existing, resolve):
    if existing is not None:
        return existing
    require(attempt == 1, 'Brak przypięć. Uruchom nowe Run workflow; Re-run nie odczytuje Latest.')
    return resolve()


def validate_state(data):
    try:
        require(data['schema'] == 1 and isinstance(data['archives'], dict), 'Invalid archives')
        require(data['current'] in data['archives'], 'Unknown current package')
        require(isinstance(data['retired'], dict) and data['current'] not in data['retired'], 'Invalid retirement')
        require(set(data['retired']) <= set(data['archives']), 'Unknown retired package')
        for until in data['retired'].values():
            timestamp(until)
        for archive in data['archives'].values():
            require(all(type(archive[k]) is int and archive[k] > 0 for k in ('release_id', 'asset_id', 'bytes')), 'Invalid archive identity')
            require(re.fullmatch('[0-9a-f]{64}', archive['sha256']) is not None, 'Invalid archive hash')
            require((isinstance(archive.get('files'), dict) and bool(archive['files']))
                    or (type(archive.get('metadata_asset_id')) is int and bool(archive.get('metadata_sha256'))), 'Missing archive inventory')
        if data['last'] is not None:
            require(data['last']['to'] == data['current'], 'Last operation differs from current')
            timestamp(data['last']['created_at'])
            timestamp(data['last']['confirmed_at'])
        pending = data['pending']
        if pending is not None:
            require(pending['from'] == data['current'] and pending['to'] in data['archives'], 'Invalid pending target')
            require(pending['archives'] == {key: data['archives'][key] for key in {pending['from'], pending['to']}}, 'Pending archive identities differ')
            require(type(pending['operation']['run_id']) is int, 'Invalid pending operation')
            timestamp(pending['operation']['created_at'])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f'Invalid publication ledger: {exc}') from exc


def prepare_transition(data, op, target, archive):
    validate_state(data)
    require(data['pending'] is None, 'pending/unknown: recover or diagnose before another publication')
    last = data['last']
    if last is not None:
        new_time, old_time = timestamp(op['created_at']), timestamp(last['created_at'])
        require(new_time != old_time or op['run_id'] == last['run_id'], 'equal timestamps, distinct operations')
        if new_time < old_time or op['run_id'] == last['run_id']:
            return None
    result = copy.deepcopy(data)
    if target in result['archives']:
        require(result['archives'][target] == archive, 'An immutable package changed')
    result['archives'][target] = archive
    result['pending'] = {'from': data['current'], 'to': target, 'operation': op,
                         'archives': {key: result['archives'][key] for key in {data['current'], target}}}
    return result


def complete_transition(data, now):
    validate_state(data)
    require(data['pending'] is not None, 'No pending operation')
    result = copy.deepcopy(data)
    pending = result['pending']
    if pending['from'] != pending['to']:
        result['retired'][pending['from']] = (timestamp(now) + timedelta(days=15)).isoformat()
    result['current'] = pending['to']
    result['retired'].pop(pending['to'], None)
    result['last'] = {**pending['operation'], 'to': pending['to'], 'confirmed_at': now}
    result['pending'] = None
    return result


def cleanup_candidates(data, now):
    validate_state(data)
    if data['pending'] is not None:
        return []
    return [key for key, until in data['retired'].items()
            if key != data['current'] and timestamp(until) <= timestamp(now)]


def build_package(site, inputs, output, package_id, app_sha):
    require(re.fullmatch(r'pages-[0-9]+', package_id) is not None, 'Invalid package ID')
    require((site / 'index.html').is_file(), 'Missing static build')
    require(re.fullmatch('[0-9a-f]{40}', app_sha) is not None, 'Application commit required')
    (site / 'inputs.json').write_bytes(inputs.read_bytes())
    (site / 'publication.json').write_bytes(encoded({'schema': 1, 'package_id': package_id,
        'app_sha': app_sha, 'inputs_sha256': digest(inputs.read_bytes())}))
    (site / '.nojekyll').touch()
    files = {}
    total = 0
    for path in sorted(site.rglob('*')):
        require(not path.is_symlink(), 'Symlinks are not accepted in static packages')
        if path.is_file():
            raw = path.read_bytes()
            files[path.relative_to(site).as_posix()] = digest(raw)
            total += len(raw)
    require(total <= 1_000_000_000, f'Static site exceeds 1 GB: {total} bytes')
    output.mkdir(parents=True, exist_ok=True)
    archive = output / 'site.tar.gz'
    with archive.open('wb') as handle, gzip.GzipFile(fileobj=handle, mode='wb', filename='', mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode='w|', format=tarfile.PAX_FORMAT) as tar:
            for name in files:
                raw = (site / name).read_bytes()
                info = tarfile.TarInfo(name)
                info.size, info.mode, info.mtime = len(raw), 0o644, 0
                tar.addfile(info, io.BytesIO(raw))
    require(archive.stat().st_size < 2 * 1024**3, 'Release archive exceeds asset limit')
    result = {'schema': 1, 'package_id': package_id, 'app_sha': app_sha, 'files': files,
        'site_bytes': total, 'bytes': archive.stat().st_size, 'sha256': digest(archive.read_bytes()),
        'manifest_sha256': files['publication.json']}
    (output / 'package.json').write_bytes(encoded(result))
    (output / 'inputs.json').write_bytes(inputs.read_bytes())
    print(f'Package {package_id}: {len(files)} files, {total} site bytes, {result["bytes"]} archive bytes')
    return result


def verify_package(path, metadata, destination=None):
    require(path.stat().st_size == metadata['bytes'] and digest(path.read_bytes()) == metadata['sha256'], 'Archive checksum differs')
    with tarfile.open(path, 'r:*') as tar:
        members = tar.getmembers()
        require(len(members) == len(metadata['files']) and {m.name for m in members} == set(metadata['files']), 'Archive inventory differs')
        for member in members:
            name = PurePosixPath(member.name)
            require(member.isfile() and not name.is_absolute() and '..' not in name.parts and '\\' not in member.name, 'Unsafe archive member')
            require(digest(tar.extractfile(member).read()) == metadata['files'][member.name], 'Archive member checksum differs')
        if destination is not None:
            require(not destination.exists(), 'Destination must be fresh')
            destination.mkdir(parents=True)
            for member in members:
                target = destination / member.name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(tar.extractfile(member).read())
                target.chmod(0o644)


class ApiError(RuntimeError):
    pass


def api(path, method='GET', payload=None, binary=False, missing_ok=False, accept='application/vnd.github+json'):
    # Binary responses and API media types are independent: artifact ZIPs use
    # the JSON API media type; release asset downloads require octet-stream.
    args = ['gh', 'api', '--method', method, path, '-H', f'Accept: {accept}']
    if payload is not None:
        args += ['--input', '-']
    result = subprocess.run(args, input=encoded(payload) if payload is not None else None,
                            capture_output=True, timeout=300)
    if missing_ok and result.returncode and '(HTTP 404)' in result.stderr.decode():
        return None
    if result.returncode:
        raise ApiError(f'GitHub {method} {path}: {result.stderr.decode()}')
    return result.stdout if binary else json.loads(result.stdout) if result.stdout else None


def require_actions():
    require(os.environ.get('GITHUB_ACTIONS') == 'true' and os.environ.get('GITHUB_REPOSITORY') == REPO,
            'Remote mutations are restricted to this repository Actions')
    require(os.environ.get('GITHUB_REF') == 'refs/heads/main', 'Dispatch main required')


def output(name, value):
    with open(os.environ['GITHUB_OUTPUT'], 'a') as handle:
        handle.write(f'{name}={value}\n')


def release(tag):
    require(re.fullmatch(r'pages-[0-9]+', tag) is not None, 'Use the exact pages-<run_id> archive tag')
    return api(f'repos/{REPO}/releases/tags/{tag}', missing_ok=True)


def download_asset(asset, path):
    raw = api(f'repos/{REPO}/releases/assets/{asset["id"]}', binary=True, accept='application/octet-stream')
    require(len(raw) == asset['size'] and asset.get('digest') == 'sha256:' + digest(raw), 'Release asset digest differs or missing')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def asset_named(record, name):
    matches = [a for a in record['assets'] if a['name'] == name]
    require(len(matches) == 1, f'Missing/ambiguous archive asset {name}')
    return matches[0]


def fetch_archive(tag, directory):
    record = release(tag)
    require(record and not record['draft'] and not record['prerelease'], 'Complete archive release missing')
    for name in ('package.json', 'site.tar.gz', 'inputs.json'):
        download_asset(asset_named(record, name), directory / name)
    metadata = json.loads((directory / 'package.json').read_bytes())
    require(metadata['package_id'] == tag, 'Archive identity differs')
    verify_package(directory / 'site.tar.gz', metadata)
    return {key: metadata[key] for key in ('package_id', 'app_sha', 'bytes', 'sha256', 'manifest_sha256', 'site_bytes')} | {
        'release_id': record['id'], 'asset_id': asset_named(record, 'site.tar.gz')['id'],
        'metadata_asset_id': asset_named(record, 'package.json')['id'],
        'metadata_sha256': digest((directory / 'package.json').read_bytes()),
        'public_files': {name: sha for name, sha in metadata['files'].items()
                         if name in ('index.html', 'publication.json', 'data/catalog.json') or name.startswith('assets/')}}


def inputs_phase(readback=False):
    run_id, attempt = int(os.environ['GITHUB_RUN_ID']), int(os.environ['GITHUB_RUN_ATTEMPT'])
    lock = BUILD / 'inputs.json'
    response = api(f'repos/{REPO}/actions/runs/{run_id}/artifacts?name=inputs-{run_id}&per_page=100')
    artifacts = [a for a in response['artifacts'] if not a['expired']]
    require(len(artifacts) <= 1, 'Ambiguous inputs artifact')
    if artifacts:
        import zipfile
        raw = api(f'repos/{REPO}/actions/artifacts/{artifacts[0]["id"]}/zip', binary=True)
        expected = artifacts[0].get('digest')
        require(expected == 'sha256:' + digest(raw), 'Inputs artifact checksum differs')
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            require(archive.namelist() == ['inputs.json'], 'Inputs artifact inventory differs')
            pinned = archive.read('inputs.json')
        if readback:
            require(lock.read_bytes() == pinned, 'Inputs readback differs')
        else:
            lock.parent.mkdir(parents=True, exist_ok=True)
            lock.write_bytes(pinned)
        json.loads(pinned)  # the pipeline validates the full source schema before fetching
        output('upload', 'false')
        return
    require(not readback, 'Inputs upload was not readable; stop before download/build')
    existing_release = release(f'pages-{run_id}') if attempt > 1 else None
    if existing_release and not existing_release['draft']:
        download_asset(asset_named(existing_release, 'inputs.json'), lock)
        output('upload', 'false')
        return
    choose_inputs(attempt, None, lambda: subprocess.run(
        ['python', 'scripts/pipeline.py', 'resolve', '--lock', str(lock)], check=True))
    output('upload', 'true')


def archive_phase():
    require_actions()
    directory = BUILD / 'package'
    metadata = json.loads((directory / 'package.json').read_bytes())
    verify_package(directory / 'site.tar.gz', metadata)
    tag = metadata['package_id']
    record = release(tag)
    if record is None:
        record = api(f'repos/{REPO}/releases', 'POST', {'tag_name': tag, 'target_commitish': metadata['app_sha'],
            'name': f'Mapa — paczka {tag}', 'body': 'Gotowa statyczna paczka mapy i przypięcia źródeł do rollbacku.',
            'draft': True, 'prerelease': False, 'make_latest': 'false'})
    require(record['draft'] or all(a['name'] in ('package.json', 'site.tar.gz', 'inputs.json') for a in record['assets']), 'Unexpected release contents')
    for name in ('site.tar.gz', 'package.json', 'inputs.json'):
        existing = [a for a in record['assets'] if a['name'] == name]
        if existing:
            require(len(existing) == 1 and existing[0].get('digest') == 'sha256:' + digest((directory / name).read_bytes()), 'Refusing to overwrite immutable archive; partial draft requires manual diagnosis or a new Run workflow')
        else:
            require(record['draft'], 'Published archive incomplete: manual diagnosis required')
            subprocess.run(['gh', 'release', 'upload', tag, str(directory / name), '--repo', REPO], check=True, timeout=300)
    api(f'repos/{REPO}/releases/{record["id"]}', 'PATCH', {'draft': False, 'make_latest': 'false'})
    fetch_archive(tag, BUILD / 'archive-readback')


def read_state():
    response = api(f'{STATE_PATH}?ref={BRANCH}', missing_ok=True)
    require(response is not None, 'Missing pages-state/state.json; publication stopped. Restore the existing ledger before retrying.')
    data = json.loads(base64.b64decode(response['content']))
    validate_state(data)
    return data, response['sha']


def save_state(data, sha):
    validate_state(data)
    payload = {'branch': BRANCH, 'message': 'Record Pages publication state', 'content': base64.b64encode(encoded(data)).decode()}
    if sha:
        payload['sha'] = sha
    try:
        api(STATE_PATH, 'PUT', payload)
    except (ApiError, OSError, subprocess.TimeoutExpired) as error:
        print(f'Uncertain write response; readback only: {error}')
    actual, _ = read_state()
    require(actual == data, 'Ledger CAS/readback differs: stop, no deploy')


def operation():
    require_actions()
    run_id, attempt = int(os.environ['GITHUB_RUN_ID']), int(os.environ['GITHUB_RUN_ATTEMPT'])
    run = api(f'repos/{REPO}/actions/runs/{run_id}')
    require(run['head_sha'] == os.environ['GITHUB_SHA'] and run['event'] == 'workflow_dispatch'
            and run['head_branch'] == 'main', 'Run identity differs')
    return {'run_id': run_id, 'run_attempt': attempt, 'head_sha': run['head_sha'], 'created_at': run['created_at'],
            'job_name': f'publish-{run_id}-{attempt}', 'step_name': STEP}


def exact_step(op, success=False):
    run = api(f'repos/{REPO}/actions/runs/{op["run_id"]}')
    require(run['head_sha'] == op['head_sha'] and run['created_at'] == op['created_at'], 'Run identity changed')
    jobs, page = [], 1
    while True:
        result = api(f'repos/{REPO}/actions/runs/{op["run_id"]}/attempts/{op["run_attempt"]}/jobs?per_page=100&page={page}')
        jobs.extend(result['jobs'])
        if len(jobs) >= result['total_count']:
            break
        require(result['jobs'] and page < 100, 'Incomplete Jobs pagination')
        page += 1
    found = [j for j in jobs if j['name'] == op['job_name']]
    require(len(found) == 1, 'Exact job missing/ambiguous')
    job = found[0]
    require(job['run_id'] == op['run_id'] and job['run_attempt'] == op['run_attempt'] and job['head_sha'] == op['head_sha'], 'Job identity differs')
    require('job_id' not in op or op['job_id'] == job['id'], 'Job ID differs')
    steps = [s for s in job['steps'] if s['name'] == op['step_name']]
    require(len(steps) == 1, 'Exact deployment step missing/ambiguous')
    step = steps[0]
    require('step_number' not in op or op['step_number'] == step['number'], 'Step number differs')
    if success:
        require(step['status'] == 'completed' and step['conclusion'] == 'success',
                'Deploy is unknown; preserve pending and diagnose manually')
    return {'job_id': job['id'], 'step_number': step['number']}


def public_check(metadata):
    files = metadata.get('public_files', metadata.get('files', {}))
    names = [name for name in files if name == 'index.html' or name == 'publication.json'
             or name == 'data/catalog.json' or name.startswith('assets/')]
    last_error = None
    for attempt in range(6):
        try:
            for name in names:
                request = urllib.request.Request(PUBLIC + name + f'?verify={time.time_ns()}', headers={'Cache-Control': 'no-cache'})
                with urllib.request.urlopen(request, timeout=20) as response:
                    require(digest(response.read()) == files[name], f'Public file differs: {name}')
            print(f'Public manifest and entry files verified ({len(names)} files)')
            return
        except (RuntimeError, OSError) as error:
            last_error = error
            if attempt < 5:
                time.sleep(10)
    raise RuntimeError(f'Public smoke check failed: {last_error}')


def verify_remote_archive(metadata, filename='verified.tar.gz'):
    path = BUILD / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = api(f'repos/{REPO}/releases/assets/{metadata["asset_id"]}', binary=True, accept='application/octet-stream')
    path.write_bytes(raw)
    verify_package(path, full_metadata(metadata))
    return path


def full_metadata(record):
    if 'metadata_asset_id' not in record:
        return record
    raw = api(f'repos/{REPO}/releases/assets/{record["metadata_asset_id"]}', binary=True, accept='application/octet-stream')
    require(digest(raw) == record['metadata_sha256'], 'Archive metadata checksum differs')
    metadata = json.loads(raw)
    require(all(metadata[key] == record[key] for key in ('package_id', 'app_sha', 'bytes', 'sha256', 'manifest_sha256', 'site_bytes')), 'Archive metadata identity differs')
    return metadata


def deploy_phase(phase, target):
    op = operation()
    data, sha = read_state()
    prepared_path = BUILD / 'prepared.json'
    if phase == 'prepare':
        if target == 'recover':
            if data['pending'] is None:
                print('No pending operation; no deploy or timestamp change')
                return
            pending = data['pending']
            exact_step(pending['operation'], True)
            for metadata in pending['archives'].values():
                verify_remote_archive(metadata)
            public_check(data['archives'][pending['to']])
            save_state(complete_transition(data, datetime.now(timezone.utc).isoformat()), sha)
            return
        # Evaluate ordering before downloading the target, which may already have expired.
        require(data['pending'] is None, 'pending/unknown: recover or diagnose manually')
        last = data['last']
        if last is not None:
            require(timestamp(op['created_at']) != timestamp(last['created_at']) or op['run_id'] == last['run_id'], 'equal timestamps, distinct operations')
            if timestamp(op['created_at']) < timestamp(last['created_at']) or op['run_id'] == last['run_id']:
                print('Pominięto — zastąpiony nowszą lub już zakończoną operacją')
                return
        if target in data['archives']:
            metadata = data['archives'][target]
            archive_path = verify_remote_archive(metadata, 'target.tar.gz')
        else:
            metadata = fetch_archive(target, BUILD / 'target')
            archive_path = BUILD / 'target/site.tar.gz'
        transition = prepare_transition(data, op, target, metadata)
        require(transition is not None, 'Unexpected stale transition')
        verify_remote_archive(data['archives'][data['current']], 'current.tar.gz')
        verify_package(archive_path, full_metadata(metadata), BUILD / 'publish-site')
        prepared_path.write_bytes(encoded({'sha': sha, 'state': data, 'transition': transition}))
        output('ready', 'true')
    elif phase == 'pending':
        prepared = json.loads(prepared_path.read_bytes())
        require(prepared['sha'] == sha and prepared['state'] == data, 'Ledger changed after prepare')
        pending_op = prepared['transition']['pending']['operation']
        require(pending_op == op, 'Prepared operation changed')
        for attempt in range(6):
            try:
                pending_op.update(exact_step(op))
                break
            except RuntimeError:
                if attempt == 5:
                    raise
                time.sleep(5)
        save_state(prepared['transition'], sha)
    elif phase == 'confirm':
        require(data['pending'] is not None, 'Pending missing')
        pending = data['pending']
        require(all(pending['operation'][key] == value for key, value in op.items()), 'Another operation owns pending')
        exact_step(pending['operation'], True)
        metadata = data['archives'][pending['to']]
        save_state(complete_transition(data, datetime.now(timezone.utc).isoformat()), sha)
        public_check(metadata)  # a failed smoke check does not erase successful deployment history


def cleanup_phase():
    require_actions()
    data, sha = read_state()
    candidates = cleanup_candidates(data, datetime.now(timezone.utc).isoformat())
    if not candidates:
        return
    # A queued rollback can refer to an expired package. Defer cleanup whenever
    # any other run is unfinished, avoiding a separate registry of candidates.
    for status in ('queued', 'in_progress', 'waiting', 'pending', 'requested'):
        response = api(f'repos/{REPO}/actions/runs?status={status}&per_page=100')
        if response['total_count'] > 100 or any(r['id'] != int(os.environ['GITHUB_RUN_ID']) for r in response['workflow_runs']):
            print('Cleanup deferred: another run is unfinished')
            return
    for key in candidates:
        metadata = data['archives'][key]
        # Preserve the historical trial release: it contains other probe archives.
        if not re.fullmatch(r'pages-[0-9]+', key):
            continue
        current, current_sha = read_state()
        require(current == data and current_sha == sha, 'Ledger changed before cleanup')
        api(f'repos/{REPO}/releases/{metadata["release_id"]}', 'DELETE', missing_ok=True)
        data['retired'].pop(key)
        data['archives'].pop(key)
        save_state(data, sha)
        data, sha = read_state()
        print(f'Removed expired archive {key}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['inputs', 'inputs-readback', 'reuse', 'package', 'archive', 'prepare', 'pending', 'confirm', 'cleanup'])
    parser.add_argument('--site', type=Path, default=ROOT / 'dist')
    parser.add_argument('--inputs', type=Path, default=BUILD / 'inputs.json')
    parser.add_argument('--output', type=Path, default=BUILD / 'package')
    parser.add_argument('--package-id', default='pages-' + os.environ.get('GITHUB_RUN_ID', '0'))
    parser.add_argument('--app-sha', default=os.environ.get('GITHUB_SHA'))
    parser.add_argument('--target', default=os.environ.get('PAGES_TARGET', 'pages-' + os.environ.get('GITHUB_RUN_ID', '0')))
    args = parser.parse_args()
    if args.phase == 'package':
        build_package(args.site, args.inputs, args.output, args.package_id, args.app_sha)
    elif args.phase in ('inputs', 'inputs-readback'):
        inputs_phase(args.phase == 'inputs-readback')
    elif args.phase == 'reuse':
        record = release(args.package_id)
        if record and not record['draft']:
            fetch_archive(args.package_id, BUILD / 'package')
            output('reused', 'true')
        else:
            output('reused', 'false')
    elif args.phase == 'archive':
        archive_phase()
    elif args.phase == 'cleanup':
        cleanup_phase()
    else:
        deploy_phase(args.phase, args.target)


if __name__ == '__main__':
    main()
