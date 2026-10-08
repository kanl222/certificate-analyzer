from contextlib import closing
from pathlib import Path
import sqlite3

import pytest

from certificate_analyzer.bootstrap import create_application
from certificate_analyzer.infrastructure.config.settings import Settings
from certificate_analyzer.infrastructure.transfer_archive import export_archive, import_archive


def make_app(tmp_path, name):
    return create_application(settings=Settings(database_path=str(tmp_path / name / "db.sqlite"), storage_folder=str(tmp_path / name / "certificates"), folders={}))


def employee(db, identifier, name, office):
    with closing(sqlite3.connect(db)) as connection:
        connection.execute("INSERT INTO employees(id,full_name,department,office,snils,is_management) VALUES (?,?, 'IT',?, '123',0)", (identifier, name, office))
        connection.commit()


def test_selective_export_excludes_data_and_includes_dependencies(tmp_path, certificate_file):
    with make_app(tmp_path, "source") as app:
        app.certificates.import_files([certificate_file()])
        employee(app.database.path, 123, "Other", "101")
        archive = tmp_path / "employees.cat"
        app.archive.export(archive, "long-secret-password", ["employees"])
        settings = import_archive(archive, tmp_path / "restored", "long-secret-password")
        with closing(sqlite3.connect(settings.parent / "certificates.db")) as db:
            assert db.execute("SELECT count(*) FROM certificates").fetchone()[0] == 0
            assert db.execute("SELECT count(*) FROM employees").fetchone()[0] > 0
        assert not list((settings.parent / "files").glob("*"))


def test_merge_and_replace_with_conflicts_and_backup(tmp_path, certificate_file):
    with make_app(tmp_path, "source") as source, make_app(tmp_path, "target") as target:
        source.certificates.import_files([certificate_file()])
        employee(source.database.path, 100, "Person", "NEW")
        employee(target.database.path, 2, "Person", "OLD")
        source.certificate_requests.create_request(request_number="REQ-1", employee_id=100, comment="NEW")
        target.certificate_requests.create_request(request_number="REQ-1", employee_id=2, comment="OLD")
        archive = tmp_path / "source.cat"
        export_archive(source.database.path, source.certificates.storage.folder, archive, "long-secret-password")
        preview = target.archive.inspect(archive, "long-secret-password")
        assert any(item["key"] == "employees:100" for item in preview["conflicts"])
        choices = {item["key"]: "incoming" for item in preview["conflicts"]}
        result = target.archive.restore(archive, "long-secret-password", "add", choices)
        assert Path(result["backup"]).is_file()
        assert len(target.certificates.list()) == 1
        assert Path(target.certificates.list()[0].source_path).is_file()
        with closing(sqlite3.connect(target.database.path)) as db:
            assert db.execute("SELECT office FROM employees WHERE id=2").fetchone()[0] == "NEW"
            assert db.execute("SELECT comment,employee_id FROM certificate_requests WHERE request_number='REQ-1'").fetchone() == ("NEW", 2)
        preview = target.archive.inspect(archive, "long-secret-password")
        target.archive.restore(archive, "long-secret-password", "add", {item["key"]: "current" for item in preview["conflicts"]})
        assert len(target.certificates.list()) == 1
        target.archive.restore(archive, "long-secret-password", "replace")
        assert len(target.certificates.list()) == 1
        with closing(sqlite3.connect(target.database.path)) as db:
            assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_missing_decision_rolls_back_current_data(tmp_path):
    with make_app(tmp_path, "source") as source, make_app(tmp_path, "target") as target:
        employee(source.database.path, 100, "Person", "NEW")
        employee(target.database.path, 2, "Person", "OLD")
        archive = tmp_path / "source.cat"
        source.archive.export(archive, "long-secret-password")
        with pytest.raises(ValueError, match="конфликтов"):
            target.archive.restore(archive, "long-secret-password", "add")
        with closing(sqlite3.connect(target.database.path)) as db:
            assert db.execute("SELECT office FROM employees WHERE id=2").fetchone()[0] == "OLD"
        assert list((target.database.path.parent / "archive-imports").iterdir()) == []


def test_read_only_routes_archive_through_ipc(tmp_path, monkeypatch):
    from certificate_analyzer.runtime.ipc import WriteClient
    calls = []
    monkeypatch.setattr(WriteClient, "call", lambda self, *args, **kwargs: (calls.append((args, kwargs)) or ({"path": "backup.cat"}, {})))
    with make_app(tmp_path, "source") as source:
        with create_application(settings=source.settings, read_only=True) as gui:
            assert gui.archive.export("backup.cat", "long-secret-password", ["employees"]) == {"path": "backup.cat"}
    assert calls[0][0][0:2] == ("archive", "export")


def test_history_and_mchd_transfer(tmp_path, mchd_file):
    from certificate_analyzer.infrastructure.persistence.notification_history import NotificationHistoryStore
    history = [{"time": "2026-10-09", "message": "Example", "type": "info"}]
    NotificationHistoryStore().save(history)
    with make_app(tmp_path, "source") as source, make_app(tmp_path, "target") as target:
        source.mchds.import_files([mchd_file()])
        archive = tmp_path / "mchd.cat"
        export_archive(source.database.path, source.certificates.storage.folder, archive, "long-secret-password", categories=["mchds", "history"], notification_history=history)
        target.archive.restore(archive, "long-secret-password", "add")
        assert NotificationHistoryStore().load() == history
        with closing(sqlite3.connect(target.database.path)) as db:
            path = db.execute("SELECT source_path FROM mchds").fetchone()[0]
            assert Path(path).is_file()
            assert db.execute("SELECT count(*) FROM mchd_authorities").fetchone()[0] > 0


def test_export_individual_records_and_excludes_audit_history_requests(tmp_path, certificate_file):
    with make_app(tmp_path, "source") as app:
        first = app.certificates.import_files([certificate_file(name="first.pem")]).certificates[0]
        second = app.certificates.import_files([certificate_file(name="second.pem")]).certificates[0]
        choices = app.archive.export_choices()
        assert len(choices["certificates"]) == 2
        assert set(choices) == {"certificates", "employees", "mchds"}
        archive = tmp_path / "selection.cat"
        app.archive.export(archive, "long-secret-password", ["certificates"], {"certificates": [first.fingerprint_sha256], "employees": [], "mchds": []})
        restored = import_archive(archive, tmp_path / "selection-restored", "long-secret-password").parent
        with closing(sqlite3.connect(restored / "certificates.db")) as db:
            assert db.execute("SELECT fingerprint_sha256 FROM certificates").fetchall() == [(first.fingerprint_sha256,)]
            assert db.execute("SELECT count(*) FROM audit_events").fetchone()[0] == 0
            assert db.execute("SELECT count(*) FROM certificate_requests").fetchone()[0] == 0
            assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert not (restored / "notification_history.json").exists()
        assert not any(second.fingerprint_sha256 in path.name for path in restored.rglob("*"))
        with pytest.raises(ValueError):
            app.archive.export(tmp_path / "audit.cat", "long-secret-password", ["audit"])
