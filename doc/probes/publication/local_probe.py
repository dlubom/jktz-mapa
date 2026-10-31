#!/usr/bin/env python3
"""Throwaway publication-state probe: mock API, not GitHub proof.

Run: python3 doc/probes/publication/local_probe.py
Only local-results.json survives; scratch files model remote state across new
client instances. Controlled exceptions simulate interruption, not runner kill.
Integer UTC seconds, no network, no third-party packages, no product workflow.
"""

import copy
import fcntl
import hashlib
import json
import tempfile
from contextlib import contextmanager
from pathlib import Path

DAY = 86400
SOURCES = ("GPS", "JKTZ", "Georeferencer")
CASES = []


class Stop(Exception):
    pass


class Crash(Exception):
    pass


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def save(path, value):
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(encoded(value))
    tmp.replace(path)


def op(number, day, **changes):
    return dict(operation_id=str(number), created_at=day * DAY, run_id=number,
                run_attempt=1, job_id=number * 10, step_name="Publish Pages", **changes)


def validate_ledger(value):
    def text(value):
        return isinstance(value, str) and bool(value)

    def operation(value):
        assert isinstance(value, dict)
        assert all(text(value[k]) for k in ("operation_id", "step_name"))
        assert all(type(value[k]) is int and value[k] >= 0
                   for k in ("created_at", "run_id", "run_attempt", "job_id"))
        assert value["run_attempt"] > 0

    try:
        assert isinstance(value, dict) and type(value["revision"]) is int and value["revision"] >= 0
        state = value["state"]
        assert isinstance(state, dict) and text(state["current"])
        assert isinstance(state["retired"], dict) and isinstance(state["archives"], dict)
        assert all(text(k) and type(v) is int and v >= 0 for k, v in state["retired"].items())
        assert isinstance(state["candidates"], list) and all(text(p) for p in state["candidates"])
        for name, hashes in state["archives"].items():
            assert text(name) and isinstance(hashes, dict)
            assert all(text(hashes[k]) and len(hashes[k]) == 64 and set(hashes[k]) <= set("0123456789abcdef")
                       for k in ("sha256", "manifest_sha256"))
        assert state["current"] in state["archives"]
        operation(state["last"])
        pending = state["pending"]
        if pending is not None:
            assert isinstance(pending, dict)
            operation(pending["operation"])
            assert pending["from"] == state["current"] and text(pending["to"])
            assert pending["hash"] == state["archives"][pending["to"]]["manifest_sha256"]
    except (KeyError, TypeError, AssertionError):
        raise Stop("invalid ledger schema: no deploy or cleanup") from None


class MockAPI:
    def __init__(self, root):
        self.root = root
        if not (root / "api.json").exists():
            packages, archives = {}, {}
            for name in ("A", "B", "C", "orphan"):
                data = f"frozen package {name}"
                manifest = {"package_id": name, "package_sha256": digest(data.encode()),
                            "app_sha": "same-application-commit"}
                packages[name] = {"bytes": data, "manifest": manifest}
                archives[name] = {"sha256": manifest["package_sha256"],
                                  "manifest_sha256": digest(encoded(manifest))}
            save(root / "api.json", dict(packages=packages, latest={s: self.pin(s, 1)
                 for s in SOURCES}, inputs={}, jobs=[], page=None, events=[]))
            save(root / "ledger.json", dict(revision=0, state=dict(current="A", retired={},
                 last=op(0, 0), pending=None, candidates=[], archives=archives)))

    @staticmethod
    def pin(source, version):
        return dict(release_id=version, asset_id=version * 10, tag=f"v{version}",
                    commit=str(version) * 40, sha256=digest(f"{source}:{version}".encode()))

    def data(self):
        return json.loads((self.root / "api.json").read_bytes())

    def event(self, name):
        data = self.data()
        data["events"].append(name)
        save(self.root / "api.json", data)

    def read(self):
        self.event("state.GET")
        value = json.loads((self.root / "ledger.json").read_bytes())
        validate_ledger(value)
        return value["revision"], value["state"]

    def cas(self, revision, state, fault=None):
        self.event("state.PUT")
        old = json.loads((self.root / "ledger.json").read_bytes())
        if fault == "conflict":
            old["revision"] += 1
            old["state"]["other_writer"] = True
            save(self.root / "ledger.json", old)
        if revision != old["revision"] or fault in ("conflict", "before_write"):
            raise Stop(fault or "conflict")
        save(self.root / "ledger.json", dict(revision=revision + 1, state=state))
        if fault == "after_write":
            raise Stop("response lost after write")

    def checked_write(self, revision, state, fault=None):
        try:
            self.cas(revision, state, fault)
        except Stop:
            if self.read()[1] == state:
                return "confirmed by reread"
            raise Stop("reread differs: stop, no blind retry")
        assert self.read()[1] == state, "write readback mismatch"
        return "confirmed by readback"

    def inputs(self, run_id, attempt, fault=None):
        key, data = str(run_id), self.data()
        if key not in data["inputs"]:
            if attempt != 1:
                raise Stop("Uruchom nowe Run workflow")
            pins = {}
            for source in SOURCES:
                self.event(f"Latest:{source}")
                pins[source] = self.data()["latest"][source]
            if fault == "before_upload":
                raise Crash("before immutable inputs upload")
            data = self.data()
            raw = encoded(pins).decode()
            data["inputs"][key] = {"raw": raw, "sha256": digest(raw.encode())}
            save(self.root / "api.json", data)
            if fault == "after_upload":
                raise Crash("upload accepted, response lost")
        artifact = self.data()["inputs"][key]
        try:
            pins = json.loads(artifact["raw"])
            assert digest(artifact["raw"].encode()) == artifact["sha256"]
            assert set(pins) == set(SOURCES)
            assert all(set(self.pin(s, 1)) <= set(pins[s]) for s in SOURCES)
            for pin in pins.values():
                assert all(type(pin[k]) is int and pin[k] > 0 for k in ("release_id", "asset_id"))
                assert isinstance(pin["tag"], str) and pin["tag"]
                for field, length in (("commit", 40), ("sha256", 64)):
                    assert isinstance(pin[field], str) and len(pin[field]) == length
                    assert set(pin[field]) <= set("0123456789abcdef")
        except (ValueError, TypeError, KeyError, AssertionError):
            raise Stop("Uruchom nowe Run workflow") from None
        return pins

    def verify(self, state, name):
        package = self.data()["packages"].get(name)
        expected = state["archives"][name]
        if not package or digest(package["bytes"].encode()) != expected["sha256"]:
            raise Stop("missing package or changed bytes")
        if digest(encoded(package["manifest"])) != expected["manifest_sha256"]:
            raise Stop("changed manifest")

    def post(self, pending, fault=None):
        assert self.read()[1]["pending"] == pending, "pending must survive before POST"
        self.event("Pages.POST")
        data = self.data()
        data["page"] = {"package_id": pending["to"], "manifest_sha256": pending["hash"]}
        if fault != "inside_deploy":
            data["jobs"].append(dict(pending["operation"], conclusion="success"))
        save(self.root / "api.json", data)
        if fault:
            raise Crash(fault)


@contextmanager
def lock(api):
    with (api.root / "publication.lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Stop("publication lock held") from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def complete(api, revision, state, now):
    pending = state["pending"]
    if pending["from"] != pending["to"]:
        previous = state["retired"].get(pending["from"], 0)
        state["retired"][pending["from"]] = max(previous, now + 15 * DAY)
    state["current"] = pending["to"]
    state["retired"].pop(pending["to"], None)
    state["last"], state["pending"] = pending["operation"], None
    api.checked_write(revision, state)


def publish(api, operation, target, now, fault=None):
    with lock(api):
        revision, state = api.read()
        if state["pending"] is not None:
            raise Stop("unknown pending: deploy blocked")
        last = state["last"]
        if operation["created_at"] < last["created_at"]:
            raise Stop("stale operation")
        if operation["created_at"] == last["created_at"] and operation["operation_id"] != last["operation_id"]:
            raise Stop("equal timestamp, different operations")
        if operation["operation_id"] == last["operation_id"]:
            if target != state["current"]:
                raise Stop("same operation, different target")
            return "already recorded"
        for name in (state["current"], target):
            api.verify(state, name)
        state["pending"] = dict(operation=operation, **{"from": state["current"]},
                                to=target, hash=state["archives"][target]["manifest_sha256"])
        api.checked_write(revision, state)
        api.post(state["pending"], fault)
        revision, state = api.read()
        complete(api, revision, state, now)


def recover(api, now):
    with lock(api):
        revision, state = api.read()
        pending = state["pending"]
        if pending is None:
            return "already reconciled"
        data = api.data()
        fields = ("run_id", "run_attempt", "job_id", "step_name")
        exact = [j for j in data["jobs"] if all(j[k] == pending["operation"][k] for k in fields)]
        page = dict(package_id=pending["to"], manifest_sha256=pending["hash"])
        if len(exact) != 1 or exact[0]["conclusion"] != "success" or data["page"] != page:
            raise Stop("unknown: exact successful step and matching page both required")
        for name in (pending["from"], pending["to"]):
            api.verify(state, name)
        complete(api, revision, state, now)


def cleanup(api, now):
    with lock(api):
        revision, state = api.read()
        if state["pending"] is not None:
            raise Stop("unknown pending: cleanup blocked")
        deleted = [p for p, until in state["retired"].items() if until <= now
                   and p != state["current"] and p not in state["candidates"]]
        data = api.data()
        for name in deleted:
            data["packages"].pop(name, None)
            state["retired"].pop(name)
        save(api.root / "api.json", data)
        api.checked_write(revision, state)
        return deleted


def expect(error, action, message=None):
    try:
        action()
    except error as exc:
        assert message is None or message in str(exc), str(exc)
        return str(exc)
    raise AssertionError(f"expected {error.__name__}")


def case(fn):
    CASES.append(fn)
    return fn


@case
def retention_and_rollback(api):
    assert cleanup(api, 120 * DAY) == []
    assert "A" in api.data()["packages"]
    publish(api, op(1, 120), "B", 120 * DAY)
    assert api.read()[1]["retired"]["A"] == 135 * DAY
    publish(api, op(2, 121), "A", 121 * DAY)
    assert "A" not in api.read()[1]["retired"]
    publish(api, op(3, 122), "B", 122 * DAY)
    assert api.read()[1]["retired"]["A"] == 137 * DAY
    assert cleanup(api, 137 * DAY - 1) == []
    assert cleanup(api, 137 * DAY) == ["A"]
    assert {"B", "C", "orphan"} <= set(api.data()["packages"])
    return dict(current="B", A_first_expiry_day=135, A_renewed_expiry_day=137,
                boundary="kept until 137 days minus one second; eligible at day 137")


@case
def stale_and_equal_operations(api):
    publish(api, op(10, 10), "B", 10 * DAY)
    publish(api, op(20, 20), "A", 20 * DAY)
    reasons = [expect(Stop, lambda: publish(api, op(15, 15), "C", 21 * DAY), "stale"),
               expect(Stop, lambda: publish(api, op(21, 20), "C", 21 * DAY), "equal timestamp")]
    assert publish(api, op(20, 20), "A", 22 * DAY) == "already recorded"
    assert api.data()["events"].count("Pages.POST") == 2
    return dict(rejections=reasons, posts=2, current=api.read()[1]["current"])


@case
def inputs_pinning(api):
    first = api.inputs(1, 1)
    data = api.data()
    data["latest"]["Georeferencer"] = api.pin("Georeferencer", 2)
    save(api.root / "api.json", data)
    assert api.inputs(1, 2) == first and api.inputs(1, 1) == first
    second = api.inputs(2, 1)
    assert first["GPS"] == second["GPS"] and first["JKTZ"] == second["JKTZ"]
    assert first["Georeferencer"] != second["Georeferencer"]
    calls = [e for e in api.data()["events"] if e.startswith("Latest:")]
    assert calls == list(map(lambda s: f"Latest:{s}", SOURCES)) * 2
    return dict(latest_calls=calls, existing_manifest_reused=True)


@case
def invalid_and_interrupted_inputs(api):
    expect(Crash, lambda: api.inputs(1, 1, "before_upload"))
    expect(Stop, lambda: MockAPI(api.root).inputs(1, 2))
    expect(Crash, lambda: api.inputs(2, 1, "after_upload"))
    assert MockAPI(api.root).inputs(2, 2) == api.inputs(2, 1)
    for key, raw in (("3", "{broken"), ("4", encoded({"GPS": api.pin("GPS", 1)}).decode())):
        data = api.data()
        data["inputs"][key] = dict(raw=raw, sha256=digest(raw.encode()))
        save(api.root / "api.json", data)
        expect(Stop, lambda: MockAPI(api.root).inputs(int(key), 2))
    for damaged in ("empty_field", "wrong_hash"):
        data = api.data()
        pins = {s: api.pin(s, 1) for s in SOURCES}
        if damaged == "empty_field":
            pins["GPS"]["asset_id"] = None
        raw = encoded(pins).decode()
        data["inputs"]["5"] = dict(raw=raw, sha256="wrong" if damaged == "wrong_hash" else digest(raw.encode()))
        save(api.root / "api.json", data)
        expect(Stop, lambda: MockAPI(api.root).inputs(5, 2))
    calls = [e for e in api.data()["events"] if e.startswith("Latest:")]
    assert len(calls) == 6
    return dict(latest_calls=6, rerun_latest_calls=0,
                rejected=["missing", "corrupt", "incomplete", "empty_field", "wrong_hash"],
                accepted="complete upload after lost response")


@case
def unknown_and_restart(api):
    expect(Crash, lambda: publish(api, op(1, 1), "B", DAY, "inside_deploy"))
    api = MockAPI(api.root)
    for _ in range(2):
        expect(Stop, lambda: recover(api, 120 * DAY))
        expect(Stop, lambda: publish(api, op(2, 2), "C", 120 * DAY))
        expect(Stop, lambda: cleanup(api, 120 * DAY))
        api = MockAPI(api.root)
    assert api.data()["events"].count("Pages.POST") == 1
    assert {"A", "B"} <= set(api.data()["packages"])
    assert api.read()[1]["pending"]["to"] == "B"
    return dict(posts=1, pending=api.read()[1]["pending"], page_alone_did_not_resolve=True)


@case
def exact_step_recovery(api):
    expect(Crash, lambda: publish(api, op(1, 1), "B", DAY, "after_step"))
    api = MockAPI(api.root)
    recover(api, 10 * DAY)
    state = api.read()[1]
    assert state["current"] == "B" and state["pending"] is None
    assert state["retired"]["A"] == 25 * DAY
    saved_ledger = (api.root / "ledger.json").read_bytes()
    assert recover(MockAPI(api.root), 30 * DAY) == "already reconciled"
    assert (api.root / "ledger.json").read_bytes() == saved_ledger
    assert api.data()["events"].count("Pages.POST") == 1
    return dict(confirmed_day=10, protected_until_day=25, posts=1, ledger=state,
                repeated_recovery="no POST, ledger write or retention reset")


@case
def insufficient_evidence(api):
    expect(Crash, lambda: publish(api, op(1, 1), "B", DAY, "after_step"))
    good = api.data()
    variants = [(k, 999 if k != "step_name" else "Other step")
                for k in ("run_id", "run_attempt", "job_id", "step_name")]
    rejected = []
    for key, value in variants + [("conclusion", "cancelled")]:
        bad = copy.deepcopy(good)
        bad["jobs"][0][key] = value
        save(api.root / "api.json", bad)
        expect(Stop, lambda: recover(MockAPI(api.root), 10 * DAY))
        rejected.append(key)
    for page in (None, {"package_id": "A", "manifest_sha256": good["page"]["manifest_sha256"]},
                 {"package_id": "B", "manifest_sha256": "wrong"}):
        bad = copy.deepcopy(good)
        bad["page"] = page
        save(api.root / "api.json", bad)
        expect(Stop, lambda: recover(MockAPI(api.root), 10 * DAY))
    assert api.read()[1]["pending"] is not None
    return dict(rejected_step_fields=rejected, rejected_page_variants=3, still_pending=True)


@case
def cas_reread(api):
    outcomes = {}
    for fault in ("conflict", "before_write", "after_write"):
        revision, state = api.read()
        state["cas_probe"] = fault
        start = len(api.data()["events"])
        if fault == "after_write":
            outcomes[fault] = api.checked_write(revision, state, fault)
        else:
            outcomes[fault] = expect(Stop, lambda: api.checked_write(revision, state, fault), "reread")
        events = api.data()["events"][start:]
        assert events == ["state.PUT", "state.GET"], events
        outcomes[fault] = dict(result=outcomes[fault], events=events)
    return outcomes


@case
def changed_package_and_lock(api):
    data = api.data()
    data["packages"]["B"]["bytes"] += " tampered"
    save(api.root / "api.json", data)
    expect(Stop, lambda: publish(api, op(1, 1), "B", DAY), "changed bytes")
    with lock(api):
        competitor = MockAPI(api.root)
        expect(Stop, lambda: publish(competitor, op(2, 2), "C", 2 * DAY), "lock held")
        expect(Stop, lambda: cleanup(competitor, 120 * DAY), "lock held")
    publish(MockAPI(api.root), op(2, 2), "C", 2 * DAY)
    assert api.data()["events"].count("Pages.POST") == 1
    return dict(tampered_package_rejected=True, concurrent_deploy_and_cleanup_blocked=True,
                next_operation_after_release="C", posts=1)


@case
def unreadable_ledger_blocks_cleanup(api):
    publish(api, op(1, 1), "B", DAY)
    ledger = api.root / "ledger.json"
    original, packages = ledger.read_bytes(), api.data()["packages"]
    ledger.unlink()
    expect(FileNotFoundError, lambda: cleanup(MockAPI(api.root), 120 * DAY))
    assert api.data()["packages"] == packages
    ledger.write_text("{broken")
    expect(json.JSONDecodeError, lambda: cleanup(MockAPI(api.root), 120 * DAY))
    assert api.data()["packages"] == packages
    ledger.write_bytes(original)
    return dict(rejected=["missing ledger/read failure", "corrupt ledger"],
                packages_unchanged=True, expired_package_A_still_present=True)


@case
def same_current_and_missing_archive(api):
    publish(api, op(1, 1), "A", DAY)
    assert api.read()[1]["retired"] == {}
    assert cleanup(api, 120 * DAY) == []
    good = api.data()
    for missing in ("A", "B"):
        damaged = copy.deepcopy(good)
        damaged["packages"].pop(missing)
        save(api.root / "api.json", damaged)
        expect(Stop, lambda: publish(api, op(2, 2), "B", 2 * DAY), "missing package")
        assert api.read()[1]["pending"] is None
        assert api.data()["events"].count("Pages.POST") == 1
    return dict(same_current_has_expiry=False, missing_current_and_target_rejected=True,
                posts=1, pending=None)


@case
def candidate_survives_cleanup(api):
    publish(api, op(1, 1), "B", DAY)
    publish(api, op(2, 2), "A", 2 * DAY)
    with lock(api):
        revision, state = api.read()
        state["candidates"] = ["B"]  # Fixture: rollback selected B before entering the final job.
        api.checked_write(revision, state)
    assert api.read()[1]["retired"]["B"] == 17 * DAY
    assert cleanup(MockAPI(api.root), 30 * DAY) == []
    assert "B" in api.data()["packages"]
    publish(api, op(3, 31), "B", 31 * DAY)
    return dict(candidate="B", expired_day=17, cleanup_day=30, retained=True, rollback_succeeded=True)


@case
def malformed_state_blocks_mutation(api):
    publish(api, op(1, 1), "B", DAY)
    publish(api, op(2, 2), "A", 2 * DAY)
    expect(Crash, lambda: publish(api, op(3, 3), "B", 3 * DAY, "after_step"))
    ledger = api.root / "ledger.json"
    good, packages = json.loads(ledger.read_bytes()), api.data()["packages"]
    assert api.data()["page"]["package_id"] == "B" and good["state"]["retired"]["B"] == 17 * DAY
    variants = [("pending", []), ("pending", {}), ("current", None), ("retired", []),
                ("last", []), ("candidates", False), ("archives", [])]
    for field, value in variants:
        broken = copy.deepcopy(good)
        broken["state"][field] = value
        save(ledger, broken)
        expect(Stop, lambda: cleanup(MockAPI(api.root), 30 * DAY), "invalid ledger schema")
        expect(Stop, lambda: publish(MockAPI(api.root), op(4, 31), "C", 31 * DAY), "invalid ledger schema")
        assert api.data()["packages"] == packages
        assert api.data()["events"].count("Pages.POST") == 3
    return dict(rejected_fields=[k for k, _ in variants], live_package_B_preserved=True,
                posts=3, additional_posts=0, packages_unchanged=True)


def main():
    results = []
    with tempfile.TemporaryDirectory(prefix="PROTOTYPE-publication-wipe-me-") as scratch:
        for check in CASES:
            root = Path(scratch) / check.__name__
            root.mkdir()
            try:
                observations = check(MockAPI(root))
                results.append(dict(case=check.__name__, passed=True, observations=observations))
            except Exception as exc:
                results.append(dict(case=check.__name__, passed=False, observations=f"{type(exc).__name__}: {exc}"))
    report = dict(evidence="mock API, not GitHub proof", passed=all(r["passed"] for r in results),
                  cases=results, limitations=["Controlled exceptions and fresh clients, not an OS/runner kill.",
                  "Local flock contention, not GitHub concurrency/queue semantics.",
                  "Atomic local file replacement models API persistence; no filesystem power-loss guarantee.",
                  "Candidate protection uses explicitly registered fixtures, not discovery of the GitHub queue.",
                  "Jobs history, Pages propagation, retention and API errors are supplied by this mock.",
                  "No claim of automatic recovery for unknown POST outcome; it remains blocked."])
    output = Path(__file__).with_name("local-results.json")
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(dict(evidence=report["evidence"], passed=report["passed"], cases=len(results), output=str(output))))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
