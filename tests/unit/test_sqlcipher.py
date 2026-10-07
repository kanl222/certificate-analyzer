from contextlib import closing
import importlib.util
import sqlite3

import pytest

from certificate_analyzer.infrastructure.database import sqlcipher


def test_driver_without_encryption_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(sqlcipher, "_driver", lambda: sqlite3)
    with pytest.raises(sqlcipher.SQLCipherUnavailable):
        sqlcipher.create_database(tmp_path / "reject.db", b"k" * 32)
    assert not (tmp_path / "reject.db").exists()


def test_invalid_key_rejected_before_driver_load(tmp_path):
    with pytest.raises(ValueError):
        sqlcipher.connect(tmp_path / "absent.db", b"short")
    assert not (tmp_path / "absent.db").exists()


native = pytest.mark.skipif(importlib.util.find_spec("sqlcipher3") is None, reason="Optional SQLCipher driver is not installed")


@native
def test_create_wal_and_read_only(tmp_path):
    key = b"k" * 32
    path = sqlcipher.create_database(tmp_path / "encrypted.db", key)
    assert path.read_bytes()[:16] != b"SQLite format 3\x00"
    with closing(sqlcipher.connect(path, key, read_only=False)) as writer:
        writer.execute("CREATE TABLE sample(value TEXT)")
        writer.execute("INSERT INTO sample VALUES ('private-data')")
        writer.commit()
        assert b"private-data" not in path.read_bytes()
        assert b"private-data" not in (tmp_path / "encrypted.db-wal").read_bytes()
        with closing(sqlcipher.connect(path, key)) as reader:
            assert reader.execute("SELECT value FROM sample").fetchone()[0] == "private-data"
            with pytest.raises(Exception, match="readonly"):
                reader.execute("DELETE FROM sample")
    with pytest.raises(sqlcipher.SQLCipherError):
        sqlcipher.connect(path, b"x" * 32)
    with closing(sqlite3.connect(path)) as plain:
        with pytest.raises(sqlite3.DatabaseError):
            plain.execute("SELECT * FROM sqlite_master").fetchall()
    with pytest.raises(sqlcipher.SQLCipherError):
        sqlcipher.create_database(path, key)


@native
def test_convert_wal_schema_version_and_rotate(tmp_path):
    plain_path = tmp_path / "plain.db"
    with closing(sqlite3.connect(plain_path)) as plain:
        plain.execute("PRAGMA journal_mode=WAL")
        plain.execute("PRAGMA user_version=5")
        plain.execute("PRAGMA application_id=123")
        plain.execute("CREATE TABLE sample(value TEXT)")
        plain.execute("CREATE INDEX sample_index ON sample(value)")
        plain.execute("INSERT INTO sample VALUES ('from-wal')")
        plain.commit()
        encrypted = sqlcipher.encrypt_copy(plain_path, tmp_path / "converted.db", b"a" * 32)
        assert plain.execute("SELECT value FROM sample").fetchone() == ("from-wal",)
    with closing(sqlcipher.connect(encrypted, b"a" * 32)) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 5
        assert connection.execute("PRAGMA application_id").fetchone()[0] == 123
        assert connection.execute("SELECT value FROM sample").fetchone()[0] == "from-wal"
        assert connection.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchone()[0] == "sample_index"
    rotated = sqlcipher.rotate_key_copy(encrypted, tmp_path / "rotated.db", b"a" * 32, b"b" * 32)
    with closing(sqlcipher.connect(rotated, b"b" * 32)) as connection:
        assert connection.execute("SELECT value FROM sample").fetchone()[0] == "from-wal"
    with pytest.raises(sqlcipher.SQLCipherError):
        sqlcipher.connect(rotated, b"a" * 32)
    engine = sqlcipher.create_sqlalchemy_engine(rotated, b"b" * 32)
    try:
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT value FROM sample").scalar() == "from-wal"
    finally:
        engine.dispose()


@native
def test_wrong_rotation_key_does_not_leave_destination(tmp_path):
    source = sqlcipher.create_database(tmp_path / "source.db", b"a" * 32)
    target = tmp_path / "failed.db"
    with pytest.raises(sqlcipher.SQLCipherError):
        sqlcipher.rotate_key_copy(source, target, b"x" * 32, b"b" * 32)
    assert not target.exists()
