"""Linux worker guards independent of Python/native inference progress."""

import ctypes
import os
import math
import time
import signal


def arm_worker_guard(controller_pid: int, seconds: float | None = None, *, deadline=None):
    """Kill on parent death or wall deadline, including stuck native CUDA calls."""
    if deadline is not None:
        seconds = deadline - time.monotonic()
    if seconds is None or not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("Worker deadline must be positive")
    libc = ctypes.CDLL(None, use_errno=True)
    # PR_SET_PDEATHSIG: kernel signal when the controller's process/thread exits.
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "Cannot set parent-death guard")
    # Close the race where the parent exited before prctl was armed.
    if os.getppid() != controller_pid:
        os.kill(os.getpid(), signal.SIGKILL)
    # Default OS action, NOT a Python handler delayed until a native eval returns.
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.setitimer(signal.ITIMER_REAL, seconds)
