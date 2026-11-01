#!/usr/bin/env python3
"""Compare the previous importer with cold/warm optimized builds of one lock."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from pipeline import digest, json_read, read_lock, require, tool_versions, write_json
from raster_cache import inventory


def compare(reference, candidate):
    old, new = inventory(reference), inventory(candidate)
    require(set(old) == set(new), 'File inventory differs')
    normalized = hashlib.sha256()
    for name in sorted(old):
        if name == 'build-report.json':
            left, right = [json_read((root / name).read_bytes()) for root in (reference, candidate)]
            # The time changes, and its serialized length changes the reported size.
            for report in (left, right):
                report.pop('buildSeconds', None)
                report.pop('bytes', None)
            require(left == right, f'Content differs: {name}')
            checksum = digest(json.dumps(left, sort_keys=True, separators=(',', ':')).encode())
        else:
            require(old[name] == new[name], f'Content differs: {name}')
            checksum = old[name]['sha256']
        normalized.update(name.encode() + b'\0' + checksum.encode() + b'\n')
    return {'filesCompared': len(old), 'webpFiles': sum(name.endswith('.webp') for name in old),
            'normalizedContentSha256': normalized.hexdigest()}


def run_build(script, args, destination, log, *, raster_cache=None):
    command = [sys.executable, str(script), 'build', '--lock', str(args.lock),
               '--cache', str(args.cache), '--output', str(destination)]
    if raster_cache is not None:
        command += ['--workers', '4', '--raster-cache', str(raster_cache)]
    start = time.monotonic()
    with log.open('w') as stream:
        subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True)
    return {'wallSeconds': round(time.monotonic() - start, 2),
            'buildReport': json_read((destination / 'build-report.json').read_bytes())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-script', type=Path, required=True)
    parser.add_argument('--lock', type=Path, required=True)
    parser.add_argument('--cache', type=Path, default=Path('.build/inputs'))
    parser.add_argument('--work', type=Path, default=Path('.build/equivalence'))
    parser.add_argument('--output', type=Path, default=Path('output/raster-equivalence'))
    args = parser.parse_args()
    lock = read_lock(args.lock)
    args.work.mkdir(parents=True, exist_ok=False)
    args.output.mkdir(parents=True, exist_ok=True)
    write_json(args.output / 'inputs.json', lock)
    reference, cold, warm = [args.work / name for name in ('reference', 'cold', 'warm')]
    cache = args.work / 'rasters'
    result = {'tools': tool_versions(), 'inputsSha256': digest(args.lock.read_bytes()),
              'referenceScriptSha256': digest(args.reference_script.read_bytes()), 'builds': {}}
    for name, script, target, raster_cache in [
            ('reference', args.reference_script, reference, None),
            ('cold', Path(__file__).with_name('pipeline.py'), cold, cache),
            ('warm', Path(__file__).with_name('pipeline.py'), warm, cache)]:
        print(f'Equivalence: building {name}', flush=True)
        result['builds'][name] = run_build(script, args, target, args.output / f'{name}.log', raster_cache=raster_cache)
        write_json(args.output / 'progress.json', result)
    require('Raster cache hit:' in (args.output / 'warm.log').read_text(), 'Warm build did not reuse the raster cache')
    result['coldEqualsReference'] = compare(reference, cold)
    result['warmEqualsReference'] = compare(reference, warm)
    write_json(args.output / 'result.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
