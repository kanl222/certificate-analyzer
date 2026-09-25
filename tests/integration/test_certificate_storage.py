import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography import x509
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PrivateFormat,
    NoEncryption,
)
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from certificate_analyzer.application.dto.certificate_query import CertificateQuery
from certificate_analyzer.bootstrap import create_application
from certificate_analyzer.domain.enums.certificate_status import CertificateStatus
from certificate_analyzer.infrastructure.certificates.x509_parser import X509Parser
from certificate_analyzer.infrastructure.database.session import Database
from certificate_analyzer.infrastructure.repositories.certificate_repository import (
    CertificateRepository,
)


def test_import_copies_public_file_and_persists_only_metadata(
    application, certificate_file
):
    source = certificate_file()
    original = source.read_bytes()
    result = application.certificates.import_files([source])
    assert result.imported == 1 and not result.errors
    cert = result.certificates[0]
    stored = Path(cert.source_path)
    assert stored.parent == application.certificates.storage.folder
    assert stored.name == cert.fingerprint_sha256 + ".cer"
    assert source.read_bytes() == original
    assert X509Parser.parse(stored).fingerprint_sha256 == cert.fingerprint_sha256
    assert cert.email == "ivan@example.test" and cert.employee.office == "101"
    assert cert.valid_to.tzinfo == timezone.utc
    columns = inspect(application.database.engine).get_columns("certificates")
    assert not any("BLOB" in str(c["type"]).upper() for c in columns)
    with sqlite3.connect(application.database.path) as db:
        assert db.execute("SELECT source_path FROM certificates").fetchone()[0] == str(
            stored
        )
    source.unlink()
    with create_application(settings=application.settings) as reopened:
        restored = reopened.certificates.get(cert.fingerprint_sha256)
        assert restored.source_path == str(stored)
        assert restored.email == cert.email
        assert restored.employee == cert.employee
        assert restored.valid_to == cert.valid_to


def test_duplicate_pem_der_and_unchanged_import_skip_parser(
    application, certificate_file, tmp_path
):
    source = certificate_file()
    cert = x509.load_pem_x509_certificate(source.read_bytes())
    der = tmp_path / "copy.der"
    der.write_bytes(cert.public_bytes(Encoding.DER))
    result = application.certificates.import_files([source, der])
    assert result.imported == 1
    assert len(result.certificates) == 1
    assert application.certificates.statistics()["total"] == 1
    assert len(list(application.certificates.storage.folder.glob("*.cer"))) == 1
    with patch.object(
        X509Parser, "parse_for_import", side_effect=AssertionError("must not reparse")
    ):
        repeated = application.certificates.import_files([source, der])
    assert repeated.skipped == 2 and not repeated.errors


def test_import_does_not_copy_private_key_sections(application, certificate_file):
    source = certificate_file()
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    source.write_bytes(
        source.read_bytes()
        + key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    )
    result = application.certificates.import_files([source])
    stored = Path(result.certificates[0].source_path)
    assert b"PRIVATE KEY" not in stored.read_bytes()
    assert x509.load_der_x509_certificate(stored.read_bytes())


def test_mixed_files_missing_and_same_names(application, certificate_file, tmp_path):
    a = certificate_file("a.pem")
    b = certificate_file("b.pem")
    folder = tmp_path / "nested"
    folder.mkdir()
    c = folder / "a.pem"
    c.write_bytes(b.read_bytes())
    bad = tmp_path / "bad.pem"
    bad.write_text("broken")
    result = application.certificates.import_files(
        [a, c, bad, tmp_path / "missing.cer"]
    )
    assert result.imported == 2 and len(result.errors) == 2
    assert len({r.source_path for r in result.certificates}) == 2


def test_missing_file_is_restored_and_corrupt_file_not_overwritten(
    application, certificate_file
):
    source = certificate_file()
    first = application.certificates.import_files([source]).certificates[0]
    stored = Path(first.source_path)
    stored.unlink()
    assert not application.certificates.import_files([source]).errors
    assert stored.is_file()
    stored.write_bytes(b"damaged")
    assert application.certificates.import_files([source]).errors
    assert stored.read_bytes() == b"damaged"
    assert application.certificates.statistics()["total"] == 1


def test_delete_by_fingerprint_keeps_files_and_reimport_restores_record(
    application, certificate_file
):
    source = certificate_file()
    cert = application.certificates.import_files([source]).certificates[0]
    assert application.certificates.delete_records([cert.fingerprint_sha256]) == 1
    assert source.exists() and Path(cert.source_path).exists()
    with sqlite3.connect(application.database.path) as db:
        assert db.execute("SELECT count(*) FROM certificate_sources").fetchone()[0] == 0
    assert application.certificates.import_files([source]).imported == 1


def test_sql_search_pagination_dates_and_live_status(application, certificate_file):
    source = certificate_file()
    base = X509Parser.parse(source)
    now = datetime(2026, 9, 25, 12, tzinfo=timezone.utc)
    records = [
        replace(
            base,
            fingerprint_sha256=f"{i:064X}",
            subject=f"Иванов {i:03}",
            email="test%_@example.test",
            valid_from=now - timedelta(days=100),
            valid_to=now + timedelta(days=i - 2),
        )
        for i in range(110)
    ]
    repository = application.certificates.repository
    repository.save_many(records)
    query = CertificateQuery(search="ИВАНОВ", limit=10, offset=10, sort="valid_to")
    page = repository.list(query, now=now)
    assert len(page) == 10 and page[0].fingerprint_sha256 == f"{10:064X}"
    stats = repository.statistics(CertificateQuery(), now=now)
    assert stats["total"] == 110 and stats["EXPIRED"] == 3
    assert repository.statistics(CertificateQuery(search="%_"), now=now)["total"] == 110
    assert (
        repository.statistics(CertificateQuery(search="%nope"), now=now)["total"] == 0
    )
    assert (
        repository.statistics(
            CertificateQuery(status=CertificateStatus.EXPIRED), now=now
        )["total"]
        == 3
    )
    assert (
        repository.statistics(
            CertificateQuery(date_from=now.date(), date_to=now.date()), now=now
        )["total"]
        == 1
    )
    later = repository.statistics(now=now + timedelta(days=200))
    assert later["EXPIRED"] == 110
    assert (
        repository.list(CertificateQuery(limit=None), now=now)[0].valid_to.tzinfo
        == timezone.utc
    )


def test_phonebook_enrichment_survives_restart(application, certificate_file, tmp_path):
    source = certificate_file()
    cert = application.certificates.import_files([source]).certificates[0]
    book = tmp_path / "phones.txt"
    book.write_text("| Отдел кадров | Иванов Иван | 101 | 00123 |", encoding="utf-8")
    assert application.certificates.load_phonebook(book) == 1
    source.unlink()
    with create_application(settings=application.settings) as reopened:
        assert reopened.certificates.get(cert.fingerprint_sha256).employee.phones == [
            "00123"
        ]


def test_concurrent_imports_use_independent_sessions(application, certificate_file):
    paths = [certificate_file(f"{i}.pem") for i in range(4)]
    # Use separate service instances just as GUI and worker processes would.
    with create_application(settings=application.settings) as second:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    lambda service: service.import_files(paths),
                    [application.certificates, second.certificates],
                )
            )
    assert not any(r.errors for r in results)
    assert sum(r.imported for r in results) == 4
    assert application.certificates.statistics()["total"] == 4
    assert len(list(application.certificates.storage.folder.glob("*.cer"))) == 4


def test_failed_batch_rolls_back_and_connection_remains_usable(
    application, certificate_file
):
    good = X509Parser.parse(certificate_file())
    invalid = replace(good, fingerprint_sha256="F" * 64, subject=None)
    with pytest.raises(IntegrityError):
        application.certificates.repository.save_many([good, invalid])
    assert application.certificates.statistics()["total"] == 0
    application.certificates.repository.save(good)
    assert application.certificates.statistics()["total"] == 1


def test_sqlalchemy_migrates_existing_database_with_backup(tmp_path):
    path = tmp_path / "old.sqlite"
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE employees (id INTEGER PRIMARY KEY, full_name TEXT, department TEXT, office TEXT, phones TEXT, email TEXT);
            CREATE TABLE certificates (fingerprint_sha256 TEXT PRIMARY KEY, subject TEXT NOT NULL, issuer TEXT NOT NULL,
                valid_from DATETIME NOT NULL, valid_to DATETIME NOT NULL, status TEXT NOT NULL, serial_number TEXT,
                has_private_key_link BOOLEAN NOT NULL, owner_name TEXT, source_path TEXT, employee_id INTEGER REFERENCES employees(id));
            INSERT INTO employees VALUES (1, 'Иванов', 'Отдел', '101', '123,456', 'old@example.test');
            INSERT INTO certificates VALUES ('ABC', 'Иванов', 'CA', '2020-01-01 00:00:00', '2030-01-01 00:00:00', 'EXPIRED', '001', 0, 'Иванов', '/old/cert.cer', 1);
        """)
    with Database(path) as database:
        repository = CertificateRepository(database.sessions)
        cert = repository.find_by_fingerprint("ABC")
        assert cert.email == "old@example.test" and cert.employee.phones == [
            "123",
            "456",
        ]
        assert cert.source_path == "/old/cert.cer" and cert.original_name == "cert.cer"
        assert (
            repository.list(CertificateQuery(search="ИВАНОВ"))[0].fingerprint_sha256
            == "ABC"
        )
    backups = list(tmp_path.glob("old.sqlite.*.bak"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as db:
        assert db.execute("SELECT count(*) FROM certificates").fetchone()[0] == 1
        assert "email" not in {
            row[1] for row in db.execute("PRAGMA table_info(certificates)")
        }
    with Database(path):
        pass
    assert len(list(tmp_path.glob("old.sqlite.*.bak"))) == 1


def test_reject_future_schema_without_writes(tmp_path):
    path = tmp_path / "future.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA user_version=999")
    with pytest.raises(ValueError):
        Database(path)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 999


def test_import_crosses_batch_boundary(application, certificate_file, tmp_path):
    source = certificate_file()
    paths = []
    for i in range(205):
        copy = tmp_path / f"copy-{i}.pem"
        copy.write_bytes(source.read_bytes())
        paths.append(copy)
    result = application.certificates.import_files(paths)
    assert result.imported == 1 and not result.errors
    assert application.certificates.statistics()["total"] == 1
    with sqlite3.connect(application.database.path) as db:
        assert (
            db.execute("SELECT count(*) FROM certificate_sources").fetchone()[0] == 205
        )
