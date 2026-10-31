#!/usr/bin/env python3
"""Inactive probe runtime. Mutations occur only in the approved Actions workflow."""
import argparse
import base64
import hashlib
import io
import json
import os
import subprocess
import tarfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = "dlubom/jktz-mapa"
BRANCH = "pages-probe-state"
STATE = f"repos/{REPO}/contents/state.json"
PUBLIC = "https://dlubom.github.io/jktz-mapa/"
STEP = "Publish Pages probe"
STEP_NUMBER = 6  # Setup job, checkout, prepare, upload, pending, deploy.
CATALOG_BYTES = (ROOT / "packages.json").read_bytes()
CATALOG = json.loads(CATALOG_BYTES)
TARGETS = {"publish-A": "A", "publish-B": "B", "rollback-A": "A", "restore-original": "original"}


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def api(path, method="GET", payload=None, binary=False):
    command = ["gh", "api", "--method", method, path,
               "-H", "Accept: application/octet-stream" if binary else "Accept: application/vnd.github+json"]
    if payload is not None:
        command += ["--input", "-"]
    result = subprocess.run(command, input=encoded(payload) if payload is not None else None,
                            capture_output=True, timeout=45)
    require(result.returncode == 0, f"API {method} {path}: {result.stderr.decode()}")
    return result.stdout if binary else json.loads(result.stdout)


def read_state():
    response = api(f"{STATE}?ref={BRANCH}")
    data = json.loads(base64.b64decode(response["content"]))
    require(data["schema"] == 1 and isinstance(data["retired"], dict), "invalid state schema")
    require(data["catalog_sha256"] == digest(CATALOG_BYTES), "catalog changed")
    require(data["current"] in CATALOG["packages"], "unknown current")
    require(data["current"] not in data["retired"], "current must have unlimited protection")
    require(set(data["retired"]) <= set(CATALOG["packages"]), "unknown retired package")
    for timestamp in data["retired"].values():
        require(datetime.fromisoformat(timestamp).tzinfo is not None, "retirement time lacks timezone")
    last = data["last"]
    if last is None:
        require(data["current"] == "original" and not data["retired"], "missing confirmed history")
    else:
        require(isinstance(last, dict) and all(key in last for key in
                ("run_id", "run_attempt", "created_at", "confirmed_at", "to", "head_sha", "job_id")), "invalid last operation")
        require(last["to"] == data["current"] and type(last["run_id"]) is int and last["run_id"] > 0,
                "last operation differs from current")
        for key in ("created_at", "confirmed_at"):
            require(datetime.fromisoformat(last[key].replace("Z", "+00:00")).tzinfo is not None, "invalid history time")
    require(set(data["archives"]) == set(CATALOG["packages"]), "archive inventory differs")
    for key, package in CATALOG["packages"].items():
        require(all(data["archives"][key][field] == value for field, value in package.items()), "archive identity differs")
    pending = data["pending"]
    if pending is not None:
        require(pending["from"] == data["current"] and pending["to"] in data["archives"], "pending package differs")
        require(pending["archives"] == {key: data["archives"][key] for key in {pending["from"], pending["to"]}},
                "pending archive identities differ")
        require(isinstance(pending["operation"], dict), "invalid pending operation")
    return data, response["sha"]


def save_state(data, sha):
    # Exactly one conditional PUT. An ambiguous result is resolved only by GET.
    try:
        api(STATE, "PUT", {"branch": BRANCH, "sha": sha, "message": "Record Pages probe state",
                           "content": base64.b64encode(encoded(data)).decode()})
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"Uncertain CAS response; read back, no write retry: {error}")
    actual, _ = read_state()
    require(actual == data, "CAS/readback differs: STOP, do not overwrite or deploy")


def jobs(run_id, attempt):
    result, page = [], 1
    while True:
        response = api(f"repos/{REPO}/actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100&page={page}")
        result.extend(response["jobs"])
        if len(result) >= response["total_count"]:
            return result
        require(response["jobs"] and page < 100, "incomplete Jobs pagination")
        page += 1


def operation():
    require(os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("GITHUB_REPOSITORY") == REPO,
            "mutating phases are restricted to this repository's Actions")
    require(os.environ["GITHUB_REF"] == "refs/heads/main", "main dispatch required")
    run_id, attempt = int(os.environ["GITHUB_RUN_ID"]), int(os.environ["GITHUB_RUN_ATTEMPT"])
    run = api(f"repos/{REPO}/actions/runs/{run_id}")
    require(run["head_sha"] == os.environ["GITHUB_SHA"] and run["head_branch"] == "main"
            and run["event"] == "workflow_dispatch", "run identity differs")
    name = os.environ["PROBE_OPERATION"]
    require(name in TARGETS or name == "recover", "unknown operation")
    require(os.environ.get("PROBE_PAUSE", "false") != "true" or name == "publish-B", "pause allowed only for B")
    return {"run_id": run_id, "run_attempt": attempt, "head_sha": run["head_sha"],
            "created_at": run["created_at"], "operation": name,
            "job_name": f"pages-publication-probe-{run_id}-{attempt}",
            "step_name": STEP, "step_number": STEP_NUMBER}


def exact_step(pending, success):
    op = pending["operation"]
    run = api(f"repos/{REPO}/actions/runs/{op['run_id']}")
    require(run["head_sha"] == op["head_sha"] and run["created_at"] == op["created_at"], "run identity changed")
    found = [j for j in jobs(op["run_id"], op["run_attempt"]) if j["name"] == op["job_name"]]
    require(len(found) == 1, "exact job missing/ambiguous: unknown")
    job = found[0]
    require(job["run_id"] == op["run_id"] and job["run_attempt"] == op["run_attempt"]
            and job["head_sha"] == op["head_sha"], "job identity differs")
    if "job_id" in op:
        require(job["id"] == op["job_id"], "job ID differs")
    steps = [s for s in job["steps"] if s["name"] == op["step_name"] and s["number"] == op["step_number"]]
    require(len(steps) == 1, "exact deploy step missing/ambiguous: unknown")
    if success:
        require(steps[0]["status"] == "completed" and steps[0]["conclusion"] == "success",
                "deploy not confirmed: unknown; preserve pending and both archives")
    return job["id"]  # Deliberately never require whole-job success.


def public_bytes(label):
    expected = {k: v for k, v in CATALOG["files"].items() if k != ".nojekyll"}
    expected["publication-probe.json"] = CATALOG["packages"][label]["manifest_sha256"]
    last_error = None
    for attempt in range(6):
        try:
            for path, sha in expected.items():
                request = urllib.request.Request(PUBLIC + path + f"?probe={time.time_ns()}",
                                                 headers={"Cache-Control": "no-cache"})
                try:
                    with urllib.request.urlopen(request, timeout=10) as response:
                        data = response.read()
                    require(sha is not None and digest(data) == sha, f"public bytes differ: {path}")
                except urllib.error.HTTPError as error:
                    require(sha is None and error.code == 404, f"public HTTP {error.code}: {path}")
            print(f"Public three base files and marker verified: {label}")
            return
        except (RuntimeError, OSError) as error:
            last_error = error
            if attempt < 5:
                time.sleep(10)
    raise RuntimeError(f"public verification failed: {last_error}")


def archive_bytes(label, archive):
    data = api(f"repos/{REPO}/releases/assets/{archive['asset_id']}", binary=True)
    require(len(data) == archive["bytes"] and digest(data) == archive["sha256"], "release archive hash differs")
    expected = dict(CATALOG["files"])
    if label != "original":
        expected["publication-probe.json"] = archive["manifest_sha256"]
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        members = tar.getmembers()
        require(len(members) == len(expected) and {m.name for m in members} == set(expected), "tar inventory differs")
        for member in members:
            require(member.isfile() and digest(tar.extractfile(member).read()) == expected[member.name], "tar member differs")
    return data


def prepare_site(data, directory):
    """Materialize verified files for the official Pages artifact action."""
    directory.mkdir(parents=True, exist_ok=False)
    allowed = set(CATALOG["files"]) | {"publication-probe.json"}
    with tarfile.open(fileobj=io.BytesIO(data)) as source:
        for member in source.getmembers():
            require(member.isfile() and member.name in allowed, "unsafe transport member")
            target = directory / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.extractfile(member).read())
            target.chmod(0o644)


def complete(data, sha):
    pending = data["pending"]
    now = datetime.now(timezone.utc)
    if pending["from"] != pending["to"]:
        data["retired"][pending["from"]] = (now + timedelta(days=15)).isoformat()
    data["current"] = pending["to"]
    data["retired"].pop(pending["to"], None)  # Current protection has no expiry.
    data["last"] = {**pending["operation"], "confirmed_at": now.isoformat(), "to": pending["to"]}
    data["pending"] = None
    save_state(data, sha)


def recover(data, sha):
    if data["pending"] is None:
        print("No pending operation; no deploy, no timestamp change")
        return
    exact_step(data["pending"], True)
    for label, archive in data["pending"]["archives"].items():
        archive_bytes(label, archive)
    public_bytes(data["pending"]["to"])
    complete(data, sha)


def workflow(phase):
    op = operation()
    data, sha = read_state()
    scratch = Path(os.environ["RUNNER_TEMP"]) / "pages-probe"
    if phase == "prepare":
        if op["operation"] == "recover":
            recover(data, sha)
            return
        require(data["pending"] is None, "pending/unknown: run explicit recover before any new publish")
        last = data["last"]
        if last is not None:
            require(op["created_at"] != last["created_at"] or op["run_id"] == last["run_id"], "equal timestamps, distinct runs: STOP")
            if op["created_at"] < last["created_at"] or op["run_id"] == last["run_id"]:
                print("Stale/already confirmed operation: no deploy")
                return
        label = TARGETS[op["operation"]]
        if data["current"] != label:
            archive_bytes(data["current"], data["archives"][data["current"]])
        package = archive_bytes(label, data["archives"][label])
        scratch.mkdir(parents=True, exist_ok=True)
        prepare_site(package, scratch / "site")
        (scratch / "prepared.json").write_bytes(encoded({"sha": sha, "state": data, "operation": op, "to": label}))
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write("ready=true\n")
    elif phase == "pending":
        prepared = json.loads((scratch / "prepared.json").read_bytes())
        require(prepared["sha"] == sha and prepared["state"] == data and prepared["operation"] == op,
                "state/context changed after archive preparation: STOP")
        pending = {"from": data["current"], "to": prepared["to"], "operation": op,
                   "archives": {key: data["archives"][key] for key in {data["current"], prepared["to"]}}}
        for attempt in range(6):
            try:
                op["job_id"] = exact_step(pending, False)
                break
            except RuntimeError:
                if attempt == 5:
                    raise
                time.sleep(5)
        data["pending"] = pending
        save_state(data, sha)  # Separate deploy action cannot start before durable readback.
    elif phase == "confirm":
        require(data["pending"] is not None, "pending missing")
        recorded = data["pending"]["operation"]
        require(all(recorded[k] == v for k, v in op.items()), "pending belongs to another operation")
        exact_step(data["pending"], True)
        label = data["pending"]["to"]
        complete(data, sha)  # Success history is durable even if the later smoke check fails.
        public_bytes(label)


def initial_state(release_path):
    release = json.loads(Path(release_path).read_bytes())
    require(release["tag_name"] == CATALOG["release_tag"] and not release["draft"] and not release["prerelease"], "wrong release")
    require(len(release["assets"]) == 3, "release must contain exactly three archives")
    archives = {}
    for label, package in CATALOG["packages"].items():
        matches = [a for a in release["assets"] if a["name"] == package["asset"]]
        require(len(matches) == 1, "asset missing/ambiguous")
        archives[label] = {**package, "asset_id": matches[0]["id"], "release_id": release["id"]}
        archive_bytes(label, archives[label])
    print(encoded({"schema": 1, "catalog_sha256": digest(CATALOG_BYTES), "archives": archives,
                   "current": "original", "retired": {}, "last": None, "pending": None}).decode(), end="")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "pending", "confirm", "initial-state", "check-public"])
    parser.add_argument("value", nargs="?")
    args = parser.parse_args()
    if args.phase == "initial-state":
        initial_state(args.value)
    elif args.phase == "check-public":
        require(args.value in CATALOG["packages"], "package required")
        public_bytes(args.value)
    else:
        workflow(args.phase)
