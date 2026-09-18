"""Crash-conservative, append-only, single-project GPU job accounting.

Reserve before launching a process; settle after it exits. An unsettled job consumes
its WHOLE reservation on restart. Never reset the ledger to make more budget.
"""

import fcntl
import json
import os
import time
import uuid
from pathlib import Path

from ..errors import BudgetError

LIMITS = {"seconds": 7200.0, "tokens": 25000, "cases": 72}


def append_json(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


class BudgetLedger:
    def __init__(self, path: Path, limits=None):
        self.path = Path(path)
        self.limits = dict(LIMITS if limits is None else limits)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = self.path.with_suffix(".lock").open("a")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self.lock.close()
            raise BudgetError("Another GPU controller owns the project ledger") from exc

    def events(self):
        if not self.path.exists():
            return []
        try:
            return [json.loads(line) for line in self.path.read_text().splitlines()]
        except (ValueError, UnicodeError) as exc:
            raise BudgetError("Damaged budget ledger; manual review required") from exc

    def usage(self):
        jobs = {}
        for event in self.events():
            if event["schema_version"] != 1:
                raise BudgetError("Unsupported budget schema")
            aid = event["attempt_id"]
            if event["event"] == "reserve":
                if aid in jobs:
                    raise BudgetError("Duplicate reservation")
                jobs[aid] = dict(event["reserved"], settled=False)
            elif event["event"] == "settle":
                if aid not in jobs or jobs[aid]["settled"]:
                    raise BudgetError("Unmatched settlement")
                actual = event["charged"]
                if any(actual[k] < 0 or actual[k] > jobs[aid][k] for k in LIMITS):
                    raise BudgetError("Settlement exceeds reservation")
                jobs[aid] = dict(actual, settled=True)
            else:
                raise BudgetError("Unknown budget event")
        return {k: sum(job[k] for job in jobs.values()) for k in LIMITS}

    def reserve(self, seconds: float, tokens: int, cases: int = 1, **metadata):
        requested = {"seconds": seconds, "tokens": tokens, "cases": cases}
        usage = self.usage()
        if any(requested[k] < 0 or usage[k] + requested[k] > self.limits[k] for k in LIMITS):
            raise BudgetError("Cumulative Stage 1 resource ceiling would be exceeded")
        aid = str(uuid.uuid4())
        append_json(
            self.path,
            {
                "schema_version": 1,
                "event": "reserve",
                "attempt_id": aid,
                "time_unix": time.time(),
                "reserved": requested,
                **metadata,
            },
        )
        return aid

    def settle(self, aid: str, seconds: float, tokens: int, cases: int = 1):
        reserve = next(
            (e for e in self.events() if e["event"] == "reserve" and e["attempt_id"] == aid), None
        )
        charged = {"seconds": seconds, "tokens": tokens, "cases": cases}
        if reserve is None or any(
            charged[k] < 0 or charged[k] > reserve["reserved"][k] for k in LIMITS
        ):
            raise BudgetError("Invalid settlement; keep conservative reservation")
        if any(e["event"] == "settle" and e["attempt_id"] == aid for e in self.events()):
            raise BudgetError("Cannot settle a job twice")
        append_json(
            self.path,
            {
                "schema_version": 1,
                "event": "settle",
                "attempt_id": aid,
                "time_unix": time.time(),
                "charged": charged,
            },
        )

    def close(self):
        self.lock.close()


class TokenMeter:
    """Charge ALL evaluated tokens, including prefill and rank scoring, before eval.

    This is stricter than counting only autoregressively generated tokens. A process
    crash is covered by its reservation, not by a potentially missing final counter.
    """

    def __init__(self, limit: int):
        self.limit = limit
        self.tokens = 0
        self.by_phase = {}
        self.phase = "startup"

    def charge(self, count: int):
        if count < 0 or self.tokens + count > self.limit:
            raise BudgetError("Per-job token reservation exhausted")
        self.tokens += count
        self.by_phase[self.phase] = self.by_phase.get(self.phase, 0) + count
