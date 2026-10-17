"""Checks that Linux source installers detect a still-running daemon."""

import os
from pathlib import Path
import shutil
import subprocess

import pytest


PROJECT = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(os.name != "posix" or not Path("/proc/self/cmdline").exists() or not BASH,
                                reason="Linux procfs and Bash required")


def test_daemon_process_helper_detects_only_worker_from_installation(tmp_path):
    executable = tmp_path / "certificate-analyzer"
    executable.write_text("#!/usr/bin/env bash\nwhile true; do sleep 1; done\n", encoding="utf-8")
    executable.chmod(0o755)
    helper = PROJECT / "packaging/linux/daemon-process.sh"

    def check():
        return subprocess.run(
            [BASH, "-c", 'source "$1"; daemon_is_running "$2"', "check", str(helper), str(executable)],
            check=False,
        ).returncode

    process = subprocess.Popen([str(executable), "worker"])
    try:
        assert check() == 0
    finally:
        process.terminate()
        process.wait(timeout=5)
    assert check() == 1
