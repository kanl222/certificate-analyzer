import sqlite3

import pytest

from certificate_analyzer.infrastructure.database.migrations import SCHEMA_VERSION
from certificate_analyzer.infrastructure.transfer_archive import ArchiveError, export_archive, import_archive


@pytest.fixture
def profile(tmp_path):
    storage = tmp_path / "certificates"
    storage.mkdir()
    cert = storage / ("A" * 64 + ".cer")
    cert.write_bytes(b"certificate bytes")
    mchd = tmp_path / "power.xml"
    mchd.write_bytes(b"<power/>")
    database = tmp_path / "original.db"
    with sqlite3.connect(database) as db:
        db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE certificates (fingerprint_sha256 TEXT PRIMARY KEY, source_path TEXT)")
        db.execute("CREATE TABLE certificate_sources (path TEXT PRIMARY KEY, fingerprint TEXT)")
        db.execute("CREATE TABLE mchds (source_path TEXT)")
        db.execute("INSERT INTO certificates VALUES (?, ?)", ("A" * 64, str(cert)))
        db.execute("INSERT INTO certificate_sources VALUES (?, ?)", (str(cert), "A" * 64))
        db.execute("INSERT INTO mchds VALUES (?)", (str(mchd),))
    return database, storage, mchd


def test_transfer_rewrites_paths_and_preserves_original(profile, tmp_path):
    database, storage, mchd = profile
    backup = export_archive(database, storage, tmp_path / "backup.cat", "long-secret-password")
    assert b"certificate bytes" not in backup.read_bytes()
    settings = import_archive(backup, tmp_path / "restored", "long-secret-password")
    assert settings.is_file()
    with sqlite3.connect(settings.parent / "certificates.db") as db:
        from pathlib import Path
        cert_path = Path(db.execute("SELECT source_path FROM certificates").fetchone()[0])
        mchd_path = Path(db.execute("SELECT source_path FROM mchds").fetchone()[0])
        assert cert_path.read_bytes() == b"certificate bytes"
        assert mchd_path.read_bytes() == mchd.read_bytes()
        assert cert_path.is_relative_to(settings.parent)
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT source_path FROM mchds").fetchone()[0] == str(mchd)
    with pytest.raises(ArchiveError):
        import_archive(backup, settings.parent, "long-secret-password")


def test_wrong_password_and_tampering_leave_no_profile(profile, tmp_path):
    database, storage, _ = profile
    backup = export_archive(database, storage, tmp_path / "backup.cat", "long-secret-password")
    destination = tmp_path / "restored"
    with pytest.raises(ArchiveError, match="пароль"):
        import_archive(backup, destination, "wrong-secret-password")
    data = bytearray(backup.read_bytes())
    data[-1] ^= 1
    backup.write_bytes(data)
    with pytest.raises(ArchiveError):
        import_archive(backup, destination, "long-secret-password")
    assert not destination.exists()


def test_missing_file_and_existing_archive_rejected(profile, tmp_path):
    database, storage, mchd = profile
    mchd.unlink()
    backup = tmp_path / "backup.cat"
    with pytest.raises(ArchiveError, match="отсутствует"):
        export_archive(database, storage, backup, "long-secret-password")
    assert not backup.exists()
    backup.write_bytes(b"existing")
    with pytest.raises(ArchiveError):
        export_archive(database, storage, backup, "long-secret-password")
    assert backup.read_bytes() == b"existing"


def test_real_application_can_read_restored_profile(application, certificate_file, tmp_path):
    from certificate_analyzer.bootstrap import create_application
    from certificate_analyzer.infrastructure.config.config_loader import load_settings

    application.certificates.import_files([certificate_file()])
    backup = export_archive(application.settings.database_path, application.settings.storage_folder, tmp_path / "real.cat", "long-secret-password")
    settings = import_archive(backup, tmp_path / "real-restored", "long-secret-password")
    with create_application(settings=load_settings(settings), read_only=True) as restored:
        certificates = restored.certificates.list()
        assert len(certificates) == len(application.certificates.list()) == 1
        from pathlib import Path
        assert Path(certificates[0].source_path).is_file()


def test_traversal_archive_is_rejected(profile, tmp_path):
    import io
    import os
    import zipfile
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from certificate_analyzer.infrastructure.transfer_archive import HEADER, _key

    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("certificates.db", b"invalid")
        archive.writestr("manifest.json", b"{}")
        archive.writestr("../outside.txt", b"escape")
    salt, nonce = os.urandom(16), os.urandom(12)
    header = HEADER + salt + nonce
    path = tmp_path / "hostile.cat"
    path.write_bytes(header + AESGCM(_key("long-secret-password", salt)).encrypt(nonce, payload.getvalue(), header))
    with pytest.raises(ArchiveError, match="Недопустимый"):
        import_archive(path, tmp_path / "restore-hostile", "long-secret-password")
    assert not (tmp_path / "outside.txt").exists()
    assert not (tmp_path / "restore-hostile").exists()
