import json
import subprocess
import sys
from typing import ClassVar

from certificate_analyzer.cli import main
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


def test_worker_report(certificate_file, tmp_path, application):
    source = certificate_file(days=-1)
    application.certificates.import_files([source])
    source.unlink()

    class Notifier:
        calls: ClassVar[list] = []

        def check_and_notify_expired(self, *args):
            self.calls.append(args)

    notifier = Notifier()
    worker = MonitoringWorker(application=application, notifier=notifier)
    assert len(worker.run_once()) == 1
    assert (tmp_path / "reports" / "monitoring.xlsx").exists()
    assert notifier.calls == [(1, 0, 1)]
    worker.stop()
    worker.run_forever()


def test_cli_import_list_export_delete_roundtrip(certificate_file, tmp_path, capsys):
    source = certificate_file()
    assert main(["import", str(source)]) == 0
    imported = json.loads(capsys.readouterr().out)
    fingerprint = imported["data"][0]["fingerprint_sha256"]
    stored = imported["data"][0]["file_name"]
    source.unlink()
    assert main(["list", "--search", "ИВАНОВ"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["total"] == 1
    assert listed["data"][0]["file_name"] == stored
    assert main(["stats"]) == 0
    assert json.loads(capsys.readouterr().out)["total"] == 1
    report = tmp_path / "records.xlsx"
    assert main(["export", str(report), "--search", "Иванов"]) == 0
    capsys.readouterr()
    from openpyxl import load_workbook

    assert load_workbook(report).active["E5"].value == "Иванов Иван"
    assert main(["delete", fingerprint]) == 0
    assert json.loads(capsys.readouterr().out)["deleted"] == 1
    assert main(["list"]) == 0
    assert json.loads(capsys.readouterr().out)["total"] == 0
    from pathlib import Path

    assert Path(stored).is_file()


def test_importing_modules_has_no_database_side_effects(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from certificate_analyzer.bootstrap import create_application; import os; from pathlib import Path; "
            "assert not Path(os.environ['CERTIFICATE_ANALYZER_HOME']).exists()",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
