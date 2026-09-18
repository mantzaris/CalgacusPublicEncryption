import os
import signal
import subprocess
import sys
from pathlib import Path


def child(code):
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    return subprocess.run([sys.executable, "-c", code], env=env, timeout=5)


def test_worker_deadline_terminates_without_controller_watchdog():
    result = child(
        "import os,time; from llm_stego_public_key.evaluation.process_guard "
        "import arm_worker_guard; arm_worker_guard(os.getppid(),0.1); time.sleep(3)"
    )
    assert result.returncode == -signal.SIGALRM


def test_missing_controller_fails_closed():
    result = child(
        "from llm_stego_public_key.evaluation.process_guard import arm_worker_guard; "
        "arm_worker_guard(0,3)"
    )
    assert result.returncode == -signal.SIGKILL


def test_parent_death_kills_worker(tmp_path):
    # The child would write a marker after 0.3s. Its controller instead exits after
    # seeing an armed handshake. The kernel must kill the orphan before the write.
    marker = tmp_path / "escaped.txt"
    worker = (
        "import os,time; from pathlib import Path; "
        "from llm_stego_public_key.evaluation.process_guard import arm_worker_guard; "
        "arm_worker_guard(os.getppid(),3); print('armed',flush=True); "
        f"time.sleep(.3); Path({str(marker)!r}).write_text('escaped')"
    )
    parent = (
        "import subprocess,sys; "
        f"p=subprocess.Popen([sys.executable,'-c',{worker!r}],stdout=subprocess.PIPE); "
        "assert p.stdout.readline().strip()==b'armed'"
    )
    assert child(parent).returncode == 0
    import time

    time.sleep(0.4)
    assert not marker.exists()
