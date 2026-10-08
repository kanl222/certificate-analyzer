from contextlib import closing
from pathlib import Path
import sqlite3

import pytest

from certificate_analyzer.infrastructure.database.data_upgrade import upgrade_database_copy
from certificate_analyzer.infrastructure.database.migrations import SCHEMA_VERSION


def test_legacy_upgrade_preserves_records_and_original(tmp_path):
    source = tmp_path / "legacy.db"
    with closing(sqlite3.connect(source)) as db:
        db.executescript("""
            CREATE TABLE employees(id INTEGER PRIMARY KEY, full_name TEXT, department TEXT, office TEXT, phones TEXT, email TEXT);
            CREATE TABLE certificates(fingerprint_sha256 TEXT PRIMARY KEY, subject TEXT, issuer TEXT,
              valid_from TEXT, valid_to TEXT, status TEXT, serial_number TEXT, has_private_key_link BOOLEAN,
              owner_name TEXT, source_path TEXT, employee_id INTEGER);
            INSERT INTO employees VALUES(1, 'Иванов', 'ИТ', '101', '123,456', 'test@example.test');
            INSERT INTO certificates VALUES('ABC', 'Иванов', 'CA', '2020-01-01', '2030-01-01', 'ACTIVE', '1', 0, 'Иванов', '/old/cert.cer', 1);
        """)
    result = upgrade_database_copy(source, tmp_path / "new.db")
    assert result.source_version == 0
    assert result.target_version == SCHEMA_VERSION
    with closing(sqlite3.connect(result.database_path)) as db:
        assert db.execute("SELECT email, phones_json FROM certificates").fetchone() == ('test@example.test', '["123", "456"]')
        assert db.execute("SELECT is_management FROM employees").fetchone()[0] == 0
        assert db.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    with closing(sqlite3.connect(source)) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 0
        assert "is_management" not in {row[1] for row in db.execute("PRAGMA table_info(employees)")}
    with pytest.raises(ValueError):
        upgrade_database_copy(source, result.database_path)


def test_future_database_rejected_without_destination(tmp_path):
    source = tmp_path / "future.db"
    with closing(sqlite3.connect(source)) as db:
        db.execute("PRAGMA user_version=999")
    with pytest.raises(ValueError, match="новее"):
        upgrade_database_copy(source, tmp_path / "new.db")
    assert not (tmp_path / "new.db").exists()


@pytest.mark.parametrize("version", [1, 2, 3, 4, 5])
def test_supported_intermediate_versions(application, tmp_path, version):
    source = Path(application.settings.database_path)
    with closing(sqlite3.connect(source)) as db:
        db.execute("INSERT INTO employees (id, full_name, phones, email, office, department, is_management) VALUES (1, 'Иванов', '123', 'test@example.test', '101', 'ИТ', 0)")
        if version < 2:
            for column in ("position", "inn", "snils", "birth_date"):
                db.execute(f"ALTER TABLE employees DROP COLUMN {column}")
        if version < 3:
            db.execute("DROP TABLE audit_events")
            for column in ("file_name", "size", "first_seen_at", "last_seen_at"):
                db.execute(f"ALTER TABLE certificate_sources DROP COLUMN {column}")
        if version < 4:
            db.execute("DROP TABLE mchd_authorities")
        if version < 5:
            db.execute("ALTER TABLE employees DROP COLUMN is_management")
        db.execute(f"PRAGMA user_version={version}")
        db.commit()
    result = upgrade_database_copy(source, tmp_path / f"version-{version}.db")
    assert result.source_version == version
    with closing(sqlite3.connect(result.database_path)) as db:
        assert db.execute("SELECT full_name, email FROM employees WHERE id=1").fetchone() == ('Иванов', 'test@example.test')
        assert db.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    with closing(sqlite3.connect(source)) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == version


def test_failed_migration_never_publishes_copy(application, tmp_path, monkeypatch):
    from certificate_analyzer.infrastructure.database import data_upgrade
    source = Path(application.settings.database_path)
    original = source.read_bytes()

    def fail(engine, path):
        raise ValueError("Test migration failure")

    monkeypatch.setattr(data_upgrade, "migrate", fail)
    destination = tmp_path / "failed.db"
    with pytest.raises(ValueError, match="failure"):
        upgrade_database_copy(source, destination)
    assert not destination.exists()
    assert source.read_bytes() == original


def test_import_older_archive_upgrades_before_publication(application, certificate_file, tmp_path):
    import io
    import os
    import zipfile
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from certificate_analyzer.infrastructure.transfer_archive import HEADER, _key, export_archive, import_archive

    application.certificates.import_files([certificate_file()])
    archive = export_archive(Path(application.settings.database_path), Path(application.settings.storage_folder), tmp_path / "backup.cat", "long-secret-password")
    envelope = archive.read_bytes()
    offset = len(HEADER)
    payload = AESGCM(_key("long-secret-password", envelope[offset:offset + 16])).decrypt(envelope[offset + 16:offset + 28], envelope[offset + 28:], envelope[:offset + 28])
    with zipfile.ZipFile(io.BytesIO(payload)) as original:
        contents = {name: original.read(name) for name in original.namelist()}
    legacy = tmp_path / "archive-db.db"
    legacy.write_bytes(contents["certificates.db"])
    with closing(sqlite3.connect(legacy)) as db:
        db.execute("ALTER TABLE employees DROP COLUMN is_management")
        db.execute("PRAGMA user_version=4")
        db.commit()
    contents["certificates.db"] = legacy.read_bytes()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as rebuilt:
        for name, content in contents.items():
            rebuilt.writestr(name, content)
    salt, nonce = os.urandom(16), os.urandom(12)
    header = HEADER + salt + nonce
    archive.write_bytes(header + AESGCM(_key("long-secret-password", salt)).encrypt(nonce, buffer.getvalue(), header))
    settings = import_archive(archive, tmp_path / "restored", "long-secret-password")
    with closing(sqlite3.connect(settings.parent / "certificates.db")) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert "is_management" in {row[1] for row in db.execute("PRAGMA table_info(employees)")}
        assert db.execute("SELECT count(*) FROM certificates").fetchone()[0] == 1
