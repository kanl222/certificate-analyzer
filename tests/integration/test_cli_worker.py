import json
import subprocess
import sys
from typing import ClassVar

from certificate_analyzer.cli import main
from certificate_analyzer.infrastructure.config.settings import Settings
from certificate_analyzer.runtime.worker import MonitoringWorker


def test_cli_mixed_folder(certificate_file, tmp_path, capsys):
    certificate_file()
    (tmp_path / "bad.pem").write_text("bad")
    assert main(["scan", str(tmp_path)]) == 1
    result = json.loads(capsys.readouterr().out)
    assert len(result["data"]) == 1 and len(result["errors"]) == 1


def test_help_has_no_gui_import():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from certificate_analyzer.cli import main; main(['scan', '/nonexistent']); assert 'tkinter' not in sys.modules; assert 'matplotlib' not in sys.modules; assert 'win32service' not in sys.modules",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_worker_report(certificate_file, tmp_path):
    certificate_file(days=-1)

    class Notifier:
        calls: ClassVar[list] = []

        def check_and_notify_expired(self, *args):
            self.calls.append(args)

    notifier = Notifier()
    worker = MonitoringWorker(
        Settings(
            folders={"Test": str(tmp_path)}, export_folder=str(tmp_path / "reports")
        ),
        notifier,
    )
    assert len(worker.run_once()) == 1
    assert (tmp_path / "reports" / "monitoring.xlsx").exists()
    assert notifier.calls == [(1, 0, 1)]
    worker.stop()
    worker.run_forever()
