"""Unit tests for resilience patterns and hardening improvements."""

from datetime import datetime, timezone
import sqlite3
import subprocess
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from certificate_analyzer.application.services.monitoring_service import MonitoringService
from certificate_analyzer.domain.models.certificate import Certificate
from certificate_analyzer.runtime.ipc import WriteClient, WriterUnavailable
from certificate_analyzer.runtime.operations import OperationJournal
from certificate_analyzer.runtime.user_daemon import ensure_writer


def test_operation_journal_wal_and_retention(tmp_path):
    path = tmp_path / "operations.sqlite"
    OperationJournal(path)

    # Check WAL mode is enabled
    with sqlite3.connect(path) as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"

        # Insert old record (> 14 days ago) and fresh record
        conn.execute(
            "INSERT INTO operations(id, digest, state, created_at) VALUES (?, ?, 'completed', datetime('now', '-20 days'))",
            (str(uuid4()), "old_digest"),
        )
        conn.execute(
            "INSERT INTO operations(id, digest, state, created_at) VALUES (?, ?, 'completed', datetime('now', '-1 day'))",
            (str(uuid4()), "fresh_digest"),
        )
        conn.commit()

    # Re-instantiating journal triggers cleanup
    OperationJournal(path)

    with sqlite3.connect(path) as conn:
        digests = [row[0] for row in conn.execute("SELECT digest FROM operations").fetchall()]
        assert "old_digest" not in digests
        assert "fresh_digest" in digests


def test_monitoring_service_db_lock_scoping(tmp_path):
    cert = Certificate(
        fingerprint_sha256="1" * 64,
        subject="User",
        issuer="CA",
        valid_from=datetime.now(timezone.utc),
        valid_to=datetime.now(timezone.utc),
        serial_number="123",
    )
    cert_service = MagicMock()
    cert_service.list.return_value = [cert]
    cert_service.statistics.return_value = {"EXPIRED": 0, "EXPIRING_SOON": 0, "total": 1}

    report_service = MagicMock()
    notifier = MagicMock()
    settings = MagicMock()
    settings.export_folder = str(tmp_path)

    service = MonitoringService(
        certificate_service=cert_service,
        report_service=report_service,
        notification_manager=notifier,
        settings=settings,
    )

    lock = MagicMock()
    lock.__enter__ = MagicMock(return_value=None)
    lock.__exit__ = MagicMock(return_value=None)

    result = service.run_cycle(db_lock=lock)

    # Lock must be acquired and exited
    assert lock.__enter__.call_count == 1
    assert lock.__exit__.call_count == 1
    assert len(result.records) == 1


def test_ensure_writer_fast_failure(tmp_path, monkeypatch):
    settings = MagicMock()
    settings.database_path = str(tmp_path / "cert.db")
    settings.model_dump_json.return_value = "{}"

    class FailingProcess:
        returncode = 42

        def poll(self):
            return 42

    def fake_popen(*args, **kwargs):
        # Write dummy error to stderr file if provided
        stderr_file = kwargs.get("stderr")
        if stderr_file and hasattr(stderr_file, "write"):
            stderr_file.write("Crash traceback: Database is locked")
            stderr_file.flush()
        return FailingProcess()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(WriteClient, "call", MagicMock(side_effect=WriterUnavailable("unreachable")))

    with pytest.raises(WriterUnavailable) as exc_info:
        ensure_writer(settings, timeout=5)

    err = str(exc_info.value)
    assert "код 42" in err or "Crash traceback" in err


def test_write_client_transient_retry(tmp_path, monkeypatch):
    client = WriteClient(tmp_path / "db", timeout=1)
    (tmp_path / "db.ipc-token").write_text("test_token", encoding="ascii")
    (tmp_path / "db.ipc-port").write_text("54321", encoding="ascii")

    attempts = 0

    def mock_create_connection(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionRefusedError("Temporary refusal")
        sock = MagicMock()
        mock_file = MagicMock()
        mock_file.readline.return_value = b'{"ok": true, "result": "pong", "errors": {}}\n'
        sock.makefile.return_value.__enter__.return_value = mock_file
        return sock

    import socket
    monkeypatch.setattr(socket, "create_connection", mock_create_connection)

    response = client._exchange("", "ping", (), {})
    assert response["result"] == "pong"
    assert attempts == 3
