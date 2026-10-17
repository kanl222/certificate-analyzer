"""Exercise DEB lifecycle hooks without touching the real user manager."""

import os
from pathlib import Path
import shutil
import subprocess

import pytest


PROJECT = Path(__file__).resolve().parents[2]
SHELL = shutil.which("sh")
pytestmark = pytest.mark.skipif(not SHELL or os.name != "posix", reason="POSIX shell required")


def _run_hook(tmp_path, name, action, *, daemon_running=False):
    commands = tmp_path / "commands"
    commands.mkdir(exist_ok=True)
    (commands / "loginctl").write_text('#!/bin/sh\nprintf "%s %s\\n" "$TEST_UID" "$TEST_USER"\n')
    (commands / "runuser").write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$TEST_LOG"\n')
    (commands / "systemctl").write_text('#!/bin/sh\nprintf "systemctl %s\\n" "$*" >> "$TEST_LOG"\n')
    (commands / "pgrep").write_text('#!/bin/sh\nexit "$TEST_RUNNING"\n')
    for command in commands.iterdir():
        command.chmod(0o755)
    environment = os.environ.copy()
    environment.update(
        PATH=str(commands) + os.pathsep + os.environ["PATH"],
        TEST_UID=str(os.getuid()),
        TEST_USER=os.environ.get("USER", "test-user"),
        TEST_LOG=str(tmp_path / "calls.txt"),
        TEST_RUNNING="0" if daemon_running else "1",
    )
    result = subprocess.run(
        [SHELL, str(PROJECT / "packaging/linux" / name), action],
        env=environment, capture_output=True, text=True, check=False,
    )
    calls = (tmp_path / "calls.txt").read_text() if (tmp_path / "calls.txt").exists() else ""
    return result, calls


def test_upgrade_stops_old_user_service_before_unpack(tmp_path):
    if not Path(f"/run/user/{os.getuid()}").is_dir():
        pytest.skip("No active user manager")
    result, calls = _run_hook(tmp_path, "preinst", "upgrade")
    assert result.returncode == 0, result.stderr
    assert "systemctl --user stop certificate-analyzer.service" in calls


def test_removal_disables_user_service(tmp_path):
    if not Path(f"/run/user/{os.getuid()}").is_dir():
        pytest.skip("No active user manager")
    result, calls = _run_hook(tmp_path, "prerm", "remove")
    assert result.returncode == 0, result.stderr
    assert "systemctl --user disable --now certificate-analyzer.service" in calls


def test_upgrade_aborts_if_old_daemon_survives(tmp_path):
    result, _ = _run_hook(tmp_path, "preinst", "upgrade", daemon_running=True)
    assert result.returncode != 0
    assert "обновление прервано" in result.stderr
