"""Persistent, crash-conservative accounting for one bounded local allocation.

A durable prefix checkpoint detects deletion/truncation/rollback of the ledger.
This protects accidental rollback, not a filesystem owner reverting all state.
"""

import fcntl
import hashlib
import json
import math
import os
import time
import uuid
from pathlib import Path

from ..errors import BudgetError

LIMITS = {"seconds": 7200.0, "tokens": 25000, "cases": 72}
STAGE6_AUTHORIZATION_SHA256 = "a79e6ebb431cc683d0a847c3a20936d714a16f0a9abad541fc7092d31772c2f9"
MAX_LEDGER_BYTES = 2 * 1024 * 1024


def append_json(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def amounts(values):
    if not isinstance(values, dict) or set(values) != set(LIMITS):
        raise BudgetError("Invalid resource fields")
    for key, value in values.items():
        valid_type = type(value) in (int, float) if key == "seconds" else type(value) is int
        if not valid_type or not math.isfinite(value) or value < 0:
            raise BudgetError("Resource amounts must be finite, nonnegative and correctly typed")
    return values


class BudgetLedger:
    def __init__(self, path: Path, limits=None, *, create=False, anchor=None, authorization=None):
        self.path = Path(path)
        self.authorization = authorization
        if authorization is not None:
            from ..profile import canonical_json
            if (create or limits is not None or anchor is not None
                or hashlib.sha256(canonical_json(authorization)).hexdigest() != STAGE6_AUTHORIZATION_SHA256):
                raise BudgetError("Only the explicit frozen Stage 6 extension is authorized")
            limits = authorization["lifetime_limits"]
            anchor = authorization["previous_checkpoint"]
        self._limits = dict(amounts(dict(LIMITS if limits is None else limits)))
        if authorization is None and any(self._limits[k] > LIMITS[k] for k in LIMITS):
            raise BudgetError("Cannot raise project ceilings")
        self.checkpoint = self.path.with_suffix(".checkpoint.json")
        self.anchor = anchor
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.path.with_suffix(".lock")
        self.lock = self.lock_path.open("a")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if create:
                if self.path.exists() or self.checkpoint.exists() or anchor is not None:
                    raise BudgetError("Refusing to reinitialize existing accounting")
                with self.path.open("xb") as handle:
                    handle.flush()
                    os.fsync(handle.fileno())
                self._checkpoint(b"")
            self.usage()
            if authorization is not None:
                # Preserve every historical ledger byte; only advance the durable checkpoint.
                # Old launchers retain their original limits and now fail closed.
                self._checkpoint(self._raw())
        except Exception as exc:
            self.lock.close()
            if isinstance(exc, BlockingIOError):
                raise BudgetError("Another GPU controller owns the project ledger") from exc
            raise

    @property
    def limits(self):
        return dict(self._limits)

    def _checkpoint(self, raw):
        state = {
            "schema_version": 1,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "limits": self._limits,
        }
        temp = self.checkpoint.with_name(self.checkpoint.name + ".tmp")
        with temp.open("w") as handle:
            json.dump(state, handle, sort_keys=True, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, self.checkpoint)
        fd = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def _raw(self):
        try:
            if self.lock.closed:
                raise BudgetError("Ledger lock closed")
            held, current = os.fstat(self.lock.fileno()), self.lock_path.stat()
            if (held.st_dev, held.st_ino) != (current.st_dev, current.st_ino):
                raise BudgetError("Ledger lock replaced")
            with self.path.open("rb") as handle:
                raw = handle.read(MAX_LEDGER_BYTES + 1)
            if len(raw) > MAX_LEDGER_BYTES:
                raise BudgetError("Ledger size limit exceeded")
            checkpoints = []
            if self.checkpoint.exists():
                state = json.loads(self.checkpoint.read_text())
                historical_extension = self.authorization is not None and state == self.authorization["previous_checkpoint"]
                if state["schema_version"] != 1 or (state["limits"] != self._limits and not historical_extension):
                    raise BudgetError("Accounting checkpoint/limits changed")
                checkpoints.append(state)
            if self.anchor is not None:
                checkpoints.append(self.anchor)
            if not checkpoints:
                raise BudgetError("Missing checkpoint; reviewed historical anchor required")
            for state in checkpoints:
                size = state["bytes"]
                if type(size) is not int or not 0 <= size <= len(raw):
                    raise BudgetError("Ledger was truncated or reset")
                if hashlib.sha256(raw[:size]).hexdigest() != state["sha256"]:
                    raise BudgetError("Ledger prefix changed or rolled back")
            return raw
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise BudgetError("Missing or damaged accounting; manual review required") from exc

    def events(self):
        try:
            raw = self._raw()
            if raw and not raw.endswith(b"\n"):
                raise BudgetError("Incomplete ledger write")
            return [json.loads(line) for line in raw.splitlines()]
        except (ValueError, UnicodeError) as exc:
            raise BudgetError("Damaged budget ledger; manual review required") from exc

    def usage(self):
        jobs = {}
        try:
            for event in self.events():
                if event["schema_version"] != 1:
                    raise BudgetError("Unsupported budget schema")
                aid = event["attempt_id"]
                if not isinstance(aid, str) or not aid:
                    raise BudgetError("Invalid attempt ID")
                if event["event"] == "reserve":
                    requested = amounts(event["reserved"])
                    if aid in jobs or any(
                        requested[k] + sum(j[k] for j in jobs.values()) > self._limits[k]
                        for k in LIMITS
                    ):
                        raise BudgetError("Duplicate or over-budget reservation")
                    jobs[aid] = dict(requested, settled=False)
                elif event["event"] in ("settle", "overrun"):
                    if aid not in jobs or jobs[aid]["settled"]:
                        raise BudgetError("Unmatched settlement")
                    actual = amounts(event["charged"])
                    if actual["cases"] != jobs[aid]["cases"]:
                        raise BudgetError("Attempt count cannot be refunded")
                    if actual["tokens"] > jobs[aid]["tokens"] or (
                        event["event"] == "settle" and actual["seconds"] > jobs[aid]["seconds"]
                    ):
                        raise BudgetError("Settlement exceeds reservation")
                    jobs[aid] = dict(actual, settled=True)
                else:
                    raise BudgetError("Unknown budget event")
        except (KeyError, TypeError) as exc:
            raise BudgetError("Invalid ledger event") from exc
        return {k: sum(job[k] for job in jobs.values()) for k in LIMITS}

    def reserve(self, seconds: float, tokens: int, cases: int = 1, **metadata):
        requested = amounts({"seconds": seconds, "tokens": tokens, "cases": cases})
        if set(metadata) & {"schema_version", "event", "attempt_id", "time_unix", "reserved"}:
            raise BudgetError("Metadata cannot overwrite accounting fields")
        if self.authorization is not None and metadata.get("allocation_id") != self.authorization["allocation_id"]:
            raise BudgetError("New reservations must identify the authorized Stage 6 allocation")
        usage = self.usage()
        if any(usage[k] + requested[k] > self._limits[k] for k in LIMITS) or any(
            e["event"] == "overrun" for e in self.events()
        ):
            raise BudgetError("Cumulative resource ceiling or previous wall overrun")
        aid = str(uuid.uuid4())
        self._append(
            {
                "schema_version": 1,
                "event": "reserve",
                "attempt_id": aid,
                "time_unix": time.time(),
                "reserved": requested,
                **metadata,
            }
        )
        return aid

    def _append(self, event):
        self._raw()  # Check lock and durable prefix immediately before mutation.
        append_json(self.path, event)
        self._checkpoint(self._raw())

    def settle(self, aid: str, seconds: float, tokens: int, cases: int = 1, *, overrun=False):
        self.usage()
        events = self.events()
        reserve = next(
            (e for e in events if e["event"] == "reserve" and e["attempt_id"] == aid), None
        )
        charged = amounts({"seconds": seconds, "tokens": tokens, "cases": cases})
        if (
            reserve is None
            or cases != reserve["reserved"]["cases"]
            or tokens > reserve["reserved"]["tokens"]
        ):
            raise BudgetError("Invalid settlement; keep conservative reservation")
        if seconds > reserve["reserved"]["seconds"] and not overrun:
            raise BudgetError("Wall overrun must be recorded explicitly")
        if any(e["event"] != "reserve" and e["attempt_id"] == aid for e in events):
            raise BudgetError("Cannot settle a job twice")
        self._append(
            {
                "schema_version": 1,
                "event": "overrun" if overrun else "settle",
                "attempt_id": aid,
                "time_unix": time.time(),
                "charged": charged,
            }
        )

    def close(self):
        self.lock.close()


class TokenMeter:
    """Charge ALL evaluated tokens before eval; abandoned jobs retain reservations."""

    def __init__(self, limit: int):
        if type(limit) is not int or not 0 <= limit <= LIMITS["tokens"]:
            raise BudgetError("Token limit must be an integer within the project ceiling")
        self.limit = limit
        self.tokens = 0
        self.by_phase = {}
        self.phase = "startup"

    def charge(self, count: int):
        if type(count) is not int or count < 0 or self.tokens + count > self.limit:
            raise BudgetError("Invalid token charge or per-job reservation exhausted")
        self.tokens += count
        self.by_phase[self.phase] = self.by_phase.get(self.phase, 0) + count
