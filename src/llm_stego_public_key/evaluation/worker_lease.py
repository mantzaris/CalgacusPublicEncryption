"""Controller-to-worker lease checked before any model/backend import.

The inherited locked descriptor keeps the allocation exclusive through worker exit.
This is a local cooperating-process guard, not a sandbox against the account owner.
"""

import hashlib
import json
import math
import os
from pathlib import Path

from ..errors import BudgetError
from .process_guard import arm_worker_guard


def verify_worker_lease(job_path: Path, ledger_path: Path):
    aid = job_path.parent.name
    if os.environ.get("STAGE1_GOVERNED_ATTEMPT") != aid:
        raise BudgetError("Worker requires an active controller lease")
    try:
        fd = int(os.environ["STAGE1_LEDGER_FD"])
        held, expected = os.fstat(fd), ledger_path.with_suffix(".lock").stat()
        if (held.st_dev, held.st_ino) != (expected.st_dev, expected.st_ino):
            raise BudgetError("Inherited ledger descriptor mismatch")
        # A separate open must be unable to acquire the controller's active lock.
        import fcntl

        with ledger_path.with_suffix(".lock").open("a") as probe:
            try:
                fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                pass
            else:
                raise BudgetError("Controller no longer owns the ledger lock")
        raw = job_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != os.environ["STAGE1_JOB_SHA256"]:
            raise BudgetError("Worker input changed after controller launch")
        job = json.loads(raw)
        events = [json.loads(line) for line in ledger_path.read_bytes().splitlines()]
        matching = [e for e in events if e["attempt_id"] == aid]
        if len(matching) != 1 or matching[0]["event"] != "reserve":
            raise BudgetError("Worker reservation is missing, reused or already settled")
        reservation = matching[0]
        if (
            reservation["reserved"]["tokens"] != job["token_reservation"]
            or reservation["reserved"]["seconds"] != job["wall_reservation_seconds"]
            or reservation["reserved"]["cases"] != 1
            or reservation["case_id"] != job["case_id"]
            or reservation["tested_code_commit"] != job["tested_code_commit"]
        ):
            raise BudgetError("Worker input does not match its reservation")
        deadline = float(os.environ["STAGE1_DEADLINE_MONOTONIC"])
        if not math.isfinite(deadline):
            raise BudgetError("Invalid controller deadline")
        controller_pid = int(os.environ["STAGE1_CONTROLLER_PID"])
        arm_worker_guard(controller_pid, deadline=deadline)
        # Atomic one-shot consumption prevents two workers sharing one reservation.
        with (job_path.parent / "worker_claim.json").open("x") as claim:
            json.dump(
                {
                    "schema_version": 1,
                    "attempt_id": aid,
                    "pid": os.getpid(),
                    "controller_pid": controller_pid,
                    "deadline_monotonic": deadline,
                },
                claim,
            )
            claim.flush()
            os.fsync(claim.fileno())
    except (OSError, KeyError, ValueError, TypeError) as exc:
        raise BudgetError("Invalid or missing worker lease") from exc
    return job
