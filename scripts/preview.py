#!/usr/bin/env python3
"""Portable review bundles and the separate, selected-PR Pages publisher."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'dlubom/jktz-mapa'
TARGET = 'dlubom/jktz-mapa-preview'
PUBLIC = 'https://dlubom.github.io/jktz-mapa-preview/'
MAX_BYTES = 1_000_000_000


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_bytes(), object_pairs_hook=unique_pairs)


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def validate_identity(value):
    require(value.get('schema') == 1 and value.get('repository') == SOURCE, 'Invalid preview identity')
    require(value.get('pr') is None or (type(value['pr']) is int and value['pr'] > 0), 'Invalid PR number')
    for key in ('head_sha', 'merge_sha', 'base_sha'):
        require((key == 'base_sha' and value.get('pr') is None and value.get(key) is None)
                or (isinstance(value.get(key), str) and re.fullmatch('[0-9a-f]{40}', value[key])), 'Invalid commit identity')
    return {key: value[key] for key in ('schema', 'repository', 'pr', 'head_sha', 'base_sha', 'merge_sha')}


def event_identity():
    if os.environ.get('PREVIEW_IDENTITY'):
        return validate_identity(json.loads(os.environ['PREVIEW_IDENTITY']))
    event = read_json(Path(os.environ['GITHUB_EVENT_PATH']))
    commit = os.environ['GITHUB_SHA']
    pr = event.get('pull_request')
    return validate_identity(dict(schema=1, repository=SOURCE, pr=pr['number'] if pr else None,
        head_sha=pr['head']['sha'] if pr else commit,
        base_sha=pr['base']['sha'] if pr else None, merge_sha=commit))


def candidate_identity(pr, commit):
    require(pr['state'] == 'open' and pr.get('mergeable') is not False, 'PR closed or conflicted')
    require(pr['base']['repo']['full_name'] == SOURCE and pr['base']['ref'] == 'main', 'PR must target source main')
    value = validate_identity(dict(schema=1, repository=SOURCE, pr=pr['number'], head_sha=pr['head']['sha'],
                                   base_sha=pr['base']['sha'], merge_sha=pr.get('merge_commit_sha')))
    require(commit['sha'] == value['merge_sha'] and [p['sha'] for p in commit['parents']] ==
            [value['base_sha'], value['head_sha']], 'Merge parents differ from the current PR')
    return value


def api(path):
    result = subprocess.run(['gh', 'api', path], capture_output=True, check=True, timeout=60)
    return json.loads(result.stdout)


def resolve_candidate(number):
    require(number > 0, 'Positive PR number required')
    pr = api(f'repos/{SOURCE}/pulls/{number}')
    # GitHub may still be calculating the synthetic merge after a push.
    for _ in range(6):
        if pr.get('merge_commit_sha') and pr.get('mergeable') is not None:
            break
        time.sleep(5)
        pr = api(f'repos/{SOURCE}/pulls/{number}')
    require(pr.get('merge_commit_sha'), 'No current merge candidate')
    commit = api(f'repos/{SOURCE}/commits/{pr["merge_commit_sha"]}')
    return candidate_identity(pr, commit)


def safe_name(name):
    path = PurePosixPath(name)
    require(isinstance(name, str) and name and not path.is_absolute() and
            path.as_posix() == name and all(p not in ('.', '..', '.git') for p in path.parts) and
            '\\' not in name and ':' not in name and not any(ord(c) < 32 for c in name), f'Unsafe asset path: {name}')


def inventory(site):
    files = {}
    total = 0
    require(not site.is_symlink(), 'Symlink directory is forbidden')
    for path in sorted(site.rglob('*')):
        require(not path.is_symlink(), 'Symlink assets are forbidden')
        name = path.relative_to(site).as_posix()
        safe_name(name)
        if path.is_file():
            total += path.stat().st_size
            require(total <= MAX_BYTES, 'Static site exceeds 1 GB')
            if name != 'checksums.json':
                files[name] = sha(path)
        else:
            require(path.is_dir(), 'Only regular files and directories are accepted')
    return files


def banner(identity):
    label = f'PR #{identity["pr"]}' if identity['pr'] else 'build gałęzi'
    link = f'https://github.com/{SOURCE}/pull/{identity["pr"]}' if identity['pr'] else f'https://github.com/{SOURCE}/commit/{identity["head_sha"]}'
    return (f'<aside id="preview-banner" aria-label="Wersja testowa" style="position:fixed;bottom:8px;left:8px;'
            f'z-index:10000;max-width:calc(100% - 16px);padding:7px 10px;border:1px solid #b88b31;'
            f'border-radius:5px;background:#fff0c2;color:#49370f;font:12px system-ui;box-shadow:0 1px 6px #0002">'
            f'Wersja testowa · <a href="{link}" target="_blank" rel="noopener">{label}</a> · '
            f'{identity["head_sha"][:7]}</aside>')


def build_bundle(site, inputs, output, identity):
    identity = validate_identity(identity)
    require(site.resolve() != output.resolve() and site.resolve() not in output.resolve().parents, 'Output must be outside site')
    require(not output.exists(), 'Bundle output must be fresh')
    require((site / 'index.html').is_file(), 'Missing static build')
    inventory(site)
    shutil.copytree(site, output)
    shutil.copyfile(inputs, output / 'inputs.json')
    shutil.copyfile(ROOT / 'scripts/preview-server.py', output / 'serve.py')
    (output / '.nojekyll').touch()
    manifest = identity | {'inputs_sha256': sha(inputs)}
    (output / 'preview.json').write_bytes(encoded(manifest))
    index = (output / 'index.html').read_text()
    require('<body>' in index and 'id="preview-banner"' not in index, 'Expected a fresh HTML entry point')
    (output / 'index.html').write_text(index.replace('<body>', '<body>' + banner(identity), 1))
    (output / 'URUCHOMIENIE.txt').write_text(
        'Mapa JKTZ — wersja testowa\n\n'
        'Rozpakuj cały ZIP do nowego folderu. W tym folderze otwórz terminal i uruchom:\n'
        '  python3 serve.py\n'
        'Windows z Python Launcher: py -3 serve.py\n'
        'Otwórz adres wypisany przez skrypt (zwykle http://127.0.0.1:4173/).\n'
        'Zatrzymanie: Ctrl+C. Wymagany Python 3.9 lub nowszy.\n\n'
        'Nie jest potrzebny Node, GDAL, QGIS ani budowanie projektu.\n'
        'Katalogi i wszystkie plany są w paczce. Podkłady TPN/PIG/OSM oraz linki wymagają internetu.\n'
        'index.html wymaga serwera HTTP; samo otwarcie pliku nie wystarcza.\n'
        'preview.json identyfikuje kod, inputs.json przypina źródła danych, checksums.json zawiera SHA-256 plików.\n')
    (output / 'checksums.json').write_bytes(encoded(inventory(output)))
    verify_bundle(output, identity)
    return manifest


def verify_bundle(site, identity):
    expected = validate_identity(identity)
    checksums = read_json(site / 'checksums.json')
    require(isinstance(checksums, dict) and checksums, 'Missing file inventory')
    for name, checksum in checksums.items():
        safe_name(name)
        require(isinstance(checksum, str) and re.fullmatch('[0-9a-f]{64}', checksum), 'Invalid checksum')
    actual = inventory(site)
    require(set(actual) == set(checksums), 'File inventory differs')
    require(actual == checksums, 'File checksum differs')
    for name in ('index.html', 'inputs.json', 'preview.json', 'serve.py', 'URUCHOMIENIE.txt'):
        require(name in actual, f'Missing bundle entry: {name}')
    manifest = read_json(site / 'preview.json')
    require(validate_identity(manifest) == expected, 'Preview identity differs')
    require(manifest['inputs_sha256'] == actual['inputs.json'], 'Input checksum differs')
    require(banner(expected) in (site / 'index.html').read_text(), 'Missing preview identity banner')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['package', 'resolve', 'verify', 'confirm', 'summary'])
    parser.add_argument('--pr', type=int)
    parser.add_argument('--site', type=Path, default=ROOT / 'dist')
    parser.add_argument('--inputs', type=Path, default=ROOT / '.build/inputs.json')
    parser.add_argument('--output', type=Path, default=ROOT / '.build/preview')
    args = parser.parse_args()
    if args.phase == 'resolve':
        value = resolve_candidate(args.pr)
        with open(os.environ['GITHUB_OUTPUT'], 'a') as handle:
            handle.write('identity=' + json.dumps(value, separators=(',', ':')) + '\n')
            handle.write('sha=' + value['merge_sha'] + '\n')
    elif args.phase == 'package':
        build_bundle(args.site, args.inputs, args.output, event_identity())
    elif args.phase == 'verify':
        identity = validate_identity(json.loads(os.environ['PREVIEW_IDENTITY']))
        require(resolve_candidate(identity['pr']) == identity, 'PR changed since build; select it again')
        verify_bundle(args.site, identity)
    elif args.phase == 'confirm':
        expected = (args.site / 'preview.json').read_bytes()
        checksums = read_json(args.site / 'checksums.json')
        for attempt in range(36):
            try:
                for name in ('preview.json', 'index.html', 'data/catalog.json'):
                    with urllib.request.urlopen(PUBLIC + name + '?run=' + os.environ['GITHUB_RUN_ID'], timeout=30) as response:
                        raw = response.read()
                    require(raw == expected if name == 'preview.json' else hashlib.sha256(raw).hexdigest() == checksums[name], 'Public file differs')
                print(PUBLIC)
                break
            except (OSError, RuntimeError):
                if attempt == 35:
                    raise
                time.sleep(5)
    elif args.phase == 'summary':
        manifest = read_json(args.site / 'preview.json')
        url = os.environ['ARTIFACT_URL']
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as handle:
            handle.write(f'### Gotowa mapa do testów\n\n[Pobierz kompletny ZIP]({url}) (15 dni). '
                         'Rozpakuj i uruchom `python3 serve.py`. Podkłady wymagają internetu.\n\n'
                         f'Kod: `{manifest["head_sha"]}`; kandydat scalenia: `{manifest["merge_sha"]}`.\n\n'
                         f'[Opublikuj wybrany PR na stronie testowej](https://github.com/{TARGET}/actions/workflows/preview.yml).\n')


if __name__ == '__main__':
    main()
