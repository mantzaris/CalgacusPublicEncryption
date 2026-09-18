"""Regression tests for demonstrated Stage 1 review findings; CPU only."""

import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys

import pytest

from llm_stego_public_key.errors import BudgetError
from llm_stego_public_key.evaluation.budget import BudgetLedger, TokenMeter
from llm_stego_public_key.evaluation.process_guard import arm_worker_guard
from llm_stego_public_key.profile import validate_supported_profile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("smoke_controller", ROOT / "scripts/run_smoke.py")
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


@pytest.mark.parametrize("damage", ["delete", "empty", "rollback"])
def test_durable_checkpoint_rejects_deleted_or_rolled_back_ledger(tmp_path, damage):
    path = tmp_path / "budget.jsonl"
    a = BudgetLedger(path, create=True)
    old = path.read_bytes()
    a.reserve(10, 100)
    a.close()
    if damage == "delete":
        path.unlink()
    else:
        path.write_bytes(b"" if damage == "empty" else old)
    with pytest.raises(BudgetError):
        BudgetLedger(path)
    with pytest.raises(BudgetError):
        BudgetLedger(path, create=True)


def test_missing_ledger_never_implicitly_initializes(tmp_path):
    with pytest.raises(BudgetError):
        BudgetLedger(tmp_path / "missing.jsonl")


def test_recovery_of_append_before_checkpoint_is_conservative(tmp_path):
    a = BudgetLedger(tmp_path / "b.jsonl", create=True)
    old = a.checkpoint.read_bytes()
    a.reserve(10, 100)
    a.checkpoint.write_bytes(old)  # Crash after append/fsync, before checkpoint replace.
    a.close()
    b = BudgetLedger(tmp_path / "b.jsonl")
    assert b.usage() == {"seconds": 10, "tokens": 100, "cases": 1}
    b.close()


@pytest.mark.parametrize(
    "field,value",
    [
        ("seconds", -1),
        ("tokens", -1),
        ("cases", -1),
        ("seconds", math.nan),
        ("seconds", math.inf),
        ("tokens", 1.5),
        ("cases", True),
    ],
)
def test_invalid_resource_values_fail_before_append(tmp_path, field, value):
    a = BudgetLedger(tmp_path / "b.jsonl", create=True)
    original = a.path.read_bytes()
    request = {"seconds": 10, "tokens": 100, "cases": 1, field: value}
    with pytest.raises(BudgetError):
        a.reserve(**request)
    assert a.path.read_bytes() == original
    a.close()


@pytest.mark.parametrize(
    "field", ["reserved", "event", "attempt_id", "schema_version", "time_unix"]
)
def test_metadata_cannot_replace_accounting_fields(tmp_path, field):
    a = BudgetLedger(tmp_path / "b.jsonl", create=True)
    with pytest.raises(BudgetError):
        a.reserve(10, 100, **{field: {"seconds": 0, "tokens": 0, "cases": 0}})
    assert a.usage()["cases"] == 0
    a.close()


@pytest.mark.parametrize("limit", [math.inf, math.nan, -1, True, 1.5, 25001])
def test_token_limit_is_finite_bounded_integer(limit):
    with pytest.raises(BudgetError):
        TokenMeter(limit)


@pytest.mark.parametrize("count", [math.inf, math.nan, -1, True, 1.5])
def test_invalid_token_charge_is_rejected(count):
    m = TokenMeter(10)
    with pytest.raises(BudgetError):
        m.charge(count)
    assert m.tokens == 0


def test_cannot_refund_attempts_or_use_closed_ledger(tmp_path):
    a = BudgetLedger(tmp_path / "b.jsonl", create=True)
    aid = a.reserve(10, 100)
    with pytest.raises(BudgetError):
        a.settle(aid, 1, 1, cases=0)
    a.close()
    with pytest.raises(BudgetError):
        a.reserve(1, 1)


def test_overrun_is_charged_and_prevents_restart(tmp_path):
    a = BudgetLedger(tmp_path / "b.jsonl", create=True)
    aid = a.reserve(10, 100)
    a.settle(aid, 12, 100, overrun=True)
    a.close()
    a = BudgetLedger(tmp_path / "b.jsonl")
    assert a.usage()["seconds"] == 12
    with pytest.raises(BudgetError):
        a.reserve(1, 1)
    a.close()


def test_unsettled_or_missing_outcome_blocks_resume(tmp_path):
    a = BudgetLedger(tmp_path / "b.jsonl", create=True)
    aid = a.reserve(10, 100)
    with pytest.raises(BudgetError):
        controller.validate_resume(a, [])
    a.settle(aid, 1, 1)
    with pytest.raises(BudgetError):
        controller.validate_resume(a, [])
    with pytest.raises(BudgetError):
        controller.validate_resume(
            a, [{"attempt_id": aid, "failure_category": "timeout_resource_failure"}]
        )
    controller.validate_resume(
        a, [{"attempt_id": aid, "failure_category": "tokenization_serialization_drift"}]
    )
    a.close()


def test_historical_anchor_rejects_changed_prefix(tmp_path):
    a = BudgetLedger(tmp_path / "b.jsonl", create=True)
    a.reserve(1, 1)
    raw = a.path.read_bytes()
    a.close()
    anchor = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    a = BudgetLedger(tmp_path / "b.jsonl", anchor=anchor)
    a.close()
    anchor["sha256"] = "0" * 64
    with pytest.raises(BudgetError):
        BudgetLedger(tmp_path / "b.jsonl", anchor=anchor)


@pytest.mark.parametrize("change", ["batch", "tie", "payload", "context"])
def test_unsupported_profile_rejected_before_backend_import(change):
    p = json.loads((ROOT / "configs/public_profile.json").read_text())
    validate_supported_profile(p)
    if change == "batch":
        p["inference"]["n_batch"] = 4
    if change == "tie":
        p["tokens"]["rank_order"] = "unstable"
    if change == "payload":
        p["max_payload_bytes"] = 512
    if change == "context":
        p["source_context"] += " "
    with pytest.raises(ValueError, match="Unsupported"):
        # The loader must reject before importing CUDA/llama.cpp, absent in CPU venv.
        from llm_stego_public_key.codecs.llama_backend import load_model

        load_model({}, p, TokenMeter(0))


def test_expired_absolute_deadline_is_rejected_before_native_guard(monkeypatch):
    import llm_stego_public_key.evaluation.process_guard as guard

    monkeypatch.setattr(guard.time, "monotonic", lambda: 100)
    with pytest.raises(ValueError):
        arm_worker_guard(os.getppid(), deadline=99)


@pytest.mark.parametrize(
    "variant", ["valid", "no_fd", "settled", "modified_input", "late_start", "duplicate"]
)
def test_worker_requires_live_inherited_lease(tmp_path, variant):
    import time

    a = BudgetLedger(tmp_path / "budget.jsonl", create=True)
    aid = a.reserve(10, 100, case_id="cpu-only", tested_code_commit="test")
    folder = tmp_path / aid
    folder.mkdir()
    path = folder / "input.json"
    path.write_text(
        json.dumps(
            {
                "case_id": "cpu-only",
                "tested_code_commit": "test",
                "token_reservation": 100,
                "wall_reservation_seconds": 10,
            }
        )
    )
    env = dict(
        os.environ,
        PYTHONPATH=str(ROOT / "src"),
        STAGE1_GOVERNED_ATTEMPT=aid,
        STAGE1_LEDGER_FD=str(a.lock.fileno()),
        STAGE1_CONTROLLER_PID=str(os.getpid()),
        STAGE1_JOB_SHA256=hashlib.sha256(path.read_bytes()).hexdigest(),
        STAGE1_DEADLINE_MONOTONIC=str(time.monotonic() + (0.15 if variant == "late_start" else 3)),
    )
    if variant == "settled":
        a.settle(aid, 1, 1)
    if variant == "modified_input":
        path.write_text(path.read_text() + " ")
    if variant == "no_fd":
        env.pop("STAGE1_LEDGER_FD")
    code = (
        "import sys,time; from pathlib import Path; "
        "from llm_stego_public_key.evaluation.worker_lease import verify_worker_lease; "
        "verify_worker_lease(Path(sys.argv[1]),Path(sys.argv[2])); "
        + ("time.sleep(2)" if variant == "late_start" else "print('leased')")
    )
    out = subprocess.run(
        [sys.executable, "-c", code, str(path), str(a.path)],
        env=env,
        pass_fds=(a.lock.fileno(),),
        capture_output=True,
        timeout=4,
    )
    if variant == "duplicate":
        assert out.returncode == 0
        repeated = subprocess.run(
            [sys.executable, "-c", code, str(path), str(a.path)],
            env=env,
            pass_fds=(a.lock.fileno(),),
            capture_output=True,
            timeout=4,
        )
        assert repeated.returncode != 0 and b"leased" not in repeated.stdout
    elif variant == "valid":
        assert out.returncode == 0 and out.stdout.strip() == b"leased"
    elif variant == "late_start":
        assert out.returncode == -signal.SIGALRM
    else:
        assert out.returncode != 0 and b"leased" not in out.stdout
    a.close()


def test_lock_stays_held_by_inherited_worker_after_controller_closes(tmp_path):
    a = BudgetLedger(tmp_path / "budget.jsonl", create=True)
    fd = a.lock.fileno()
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; print('ready',flush=True); time.sleep(5)"],
        pass_fds=(fd,),
        stdout=subprocess.PIPE,
    )
    try:
        assert proc.stdout.readline().strip() == b"ready"
        a.close()
        with pytest.raises(BudgetError):
            BudgetLedger(tmp_path / "budget.jsonl")
    finally:
        proc.kill()
        proc.wait()
    b = BudgetLedger(tmp_path / "budget.jsonl")
    b.close()


def test_dirty_dependency_lock_blocks_claiming_clean_revision(tmp_path, monkeypatch):
    commands = []

    def check(argv, **kwargs):
        commands.append(argv)
        if argv[:3] == ["git", "diff", "HEAD"] and "requirements-cpu.lock" in argv:
            return b"dirty dependency pin"
        return b""

    monkeypatch.setattr(controller.subprocess, "check_output", check)
    with pytest.raises(RuntimeError, match="Commit code"):
        controller.revision()


def test_interrupted_controller_kills_worker_and_keeps_reservation(tmp_path, monkeypatch):
    import time

    art = tmp_path / "artifacts"
    art.mkdir()
    a = BudgetLedger(art / "budget.jsonl", create=True)
    monkeypatch.setattr(controller, "ART", art)
    monkeypatch.setattr(controller, "revision", lambda: "cpu-test")
    real_popen = subprocess.Popen
    children = []

    def cpu_process(argv, **kwargs):
        proc = real_popen([sys.executable, "-c", "import time; time.sleep(10)"], **kwargs)
        children.append(proc)
        return proc

    monkeypatch.setattr(controller.subprocess, "Popen", cpu_process)

    def interrupt(*args):
        raise KeyboardInterrupt("simulated interrupted sampler")

    monkeypatch.setattr(controller, "observed_gpu", interrupt)
    started = time.monotonic()
    with pytest.raises(KeyboardInterrupt):
        controller.execute(
            a,
            {"case_id": "interrupted", "kind": "control"},
            {"reused_site_packages": "", "gpu_uuid": "CPU-TEST"},
            "cpu-test",
        )
    assert time.monotonic() - started < 5
    assert children[0].poll() == -signal.SIGKILL
    assert a.usage() == {"seconds": 240, "tokens": 1500, "cases": 1}
    with pytest.raises(BudgetError):
        controller.validate_resume(a, [])
    a.close()


def test_nonzero_worker_exit_cannot_be_reported_success(tmp_path, monkeypatch):
    art = tmp_path / "artifacts"
    art.mkdir()
    a = BudgetLedger(art / "budget.jsonl", create=True)
    monkeypatch.setattr(controller, "ART", art)
    monkeypatch.setattr(controller, "revision", lambda: "cpu-test")
    monkeypatch.setattr(controller, "ROOT", tmp_path)
    real_popen = subprocess.Popen

    def cpu_process(argv, **kwargs):
        job = Path(argv[-1])
        code = (
            "import json,time,sys; from pathlib import Path; "
            "print('offloaded 33/33 layers to GPU',flush=True); "
            f"Path({str(job.parent / 'result.json')!r}).write_text(json.dumps("
            "{'success':True,'charged_tokens':0})); time.sleep(.05); sys.exit(1)"
        )
        return real_popen([sys.executable, "-c", code], **kwargs)

    monkeypatch.setattr(controller.subprocess, "Popen", cpu_process)
    monkeypatch.setattr(controller, "observed_gpu", lambda *args: 100)
    result = controller.execute(
        a,
        {"case_id": "nonzero", "kind": "control"},
        {"reused_site_packages": "", "gpu_uuid": "CPU-TEST"},
        "cpu-test",
    )
    assert result["success"] is False and result["exit_code"] == 1
    assert result["failure_category"] == "timeout_resource_failure"
    assert a.usage() == {"seconds": 240, "tokens": 1500, "cases": 1}
    a.close()


def test_public_observer_has_no_evaluator_or_private_inputs():
    import inspect
    from llm_stego_public_key.evaluation.observer import observe_text
    from llm_stego_public_key.cryptography.hpke import serialize

    class PublicOnlyCodec:
        def extract(self, wire, context):
            assert wire == b"public carrier" and context == "public context"
            return serialize(bytes(68))  # Syntax-valid but not an authenticated ciphertext.

    assert list(inspect.signature(observe_text).parameters) == [
        "codec",
        "transmitted_utf8",
        "cover_context",
    ]
    result = observe_text(PublicOnlyCodec(), b"public carrier", "public context")
    assert result["format_valid"] and not result["authenticated"]


def test_authenticated_replay_is_atomic_across_connections(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from llm_stego_public_key.cryptography.hpke import (
        ReplayCache,
        generate_key_pair,
        seal,
        open_message,
    )
    from llm_stego_public_key.errors import ReplayError
    from llm_stego_public_key.profile import Binding

    binding = Binding.from_profile({"cover_contexts": ["public"]}, "public")
    sk, pk = generate_key_pair()
    text = seal(b"delivered once", pk, binding)
    path = str(tmp_path / "replay.sqlite")
    ReplayCache(path).close()

    def attempt(_):
        cache = ReplayCache(path)
        try:
            return open_message(text, sk, binding, cache)
        except ReplayError:
            return "replay"
        finally:
            cache.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    assert results.count(b"delivered once") == 1 and results.count("replay") == 1


def test_missing_historical_keys_are_not_silently_regenerated(tmp_path, monkeypatch):
    monkeypatch.setattr(controller, "ART", tmp_path)
    with pytest.raises(BudgetError):
        controller.initialize_inputs()
    assert not (tmp_path / "TEST_ONLY_keys.json").exists()
