#!/usr/bin/env python3
"""Build reproducible probe archives locally; never writes to GitHub."""
import argparse
import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = "12a6783bc09eda112f9f187f9df5825264bbf183"
TAG = "pages-publication-probe-20261031"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def prepare(source_repo, output):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(source_repo), *args])
    before = json.loads((ROOT / "remote-before.json").read_text())
    expected = {x["path"]: x["expected_sha256"] for x in before["public_files"]}
    expected[".nojekyll"] = digest(b"")
    tree = git("ls-tree", "-rz", SOURCE).split(b"\0")
    blobs = {}
    for entry in filter(None, tree):
        metadata, name = entry.split(b"\t", 1)
        mode, kind, sha = metadata.decode().split()
        assert mode == "100644" and kind == "blob", "non-regular source entry"
        blobs[name.decode()] = git("cat-file", "blob", sha)
    assert {k: digest(v) for k, v in blobs.items()} == expected, "source inventory/hash differs"
    output.mkdir(parents=True, exist_ok=True)
    catalog = {"source_sha": SOURCE, "release_tag": TAG, "files": expected, "packages": {}}
    for label in ("original", "A", "B"):
        files = dict(blobs)
        marker = None
        if label != "original":
            marker = encoded({"probe": TAG, "package": label, "source_sha": SOURCE, "files": expected})
            files["publication-probe.json"] = marker
        target = output / f"{label}.tar"
        with tarfile.open(target, "w", format=tarfile.USTAR_FORMAT) as archive:
            for name, data in sorted(files.items()):
                entry = tarfile.TarInfo(name)
                entry.size, entry.mode, entry.mtime = len(data), 0o644, 0
                archive.addfile(entry, io.BytesIO(data))
        catalog["packages"][label] = {"asset": target.name, "bytes": target.stat().st_size,
                                       "sha256": digest(target.read_bytes()),
                                       "manifest_sha256": digest(marker) if marker else None}
    result = encoded(catalog)
    (output / "packages.json").write_bytes(result)
    checked = ROOT / "packages.json"
    if checked.exists():
        assert checked.read_bytes() == result, "generated catalog differs from reviewed packages.json"
    print(result.decode(), end="")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source_repo, args.output)
