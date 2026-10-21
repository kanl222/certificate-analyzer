"""Проверки настроек SQLite у процесса записи и клиентов приложения."""

import sqlite3

import pytest
from sqlalchemy.exc import OperationalError

from certificate_analyzer.infrastructure.database.session import Database


def test_sqlite_settings_apply_to_every_writer_and_reader_connection(tmp_path):
    path = tmp_path / "records.sqlite"
    with Database(path) as writer, Database(path, read_only=True) as reader:
        for database, query_only in ((writer, 0), (reader, 1)):
            with database.engine.connect() as first, database.engine.connect() as second:
                for connection in (first, second):
                    for name, expected in (
                        ("journal_mode", "wal"), ("foreign_keys", 1),
                        ("busy_timeout", 30000), ("synchronous", 2),
                        ("query_only", query_only),
                    ):
                        assert connection.exec_driver_sql(f"PRAGMA {name}").scalar() == expected


def test_writer_enforces_durable_synchronization(tmp_path, monkeypatch):
    """Окружение драйвера не может незаметно отключить синхронизацию записей."""
    connect = sqlite3.dbapi2.connect

    def without_synchronization(*args, **kwargs):
        connection = connect(*args, **kwargs)
        connection.execute("PRAGMA synchronous=OFF")
        return connection

    monkeypatch.setattr(sqlite3.dbapi2, "connect", without_synchronization)
    with Database(tmp_path / "durable.sqlite") as database:
        with database.engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA synchronous").scalar() == 2


def test_database_filename_roundtrip_with_unicode_spaces_and_uri_characters(tmp_path):
    path = tmp_path / "База #1 50%" / "сертификаты #1.sqlite"
    with Database(path) as writer:
        with writer.engine.begin() as connection:
            connection.exec_driver_sql("INSERT INTO employees (full_name, department, office, phones, email, is_management) VALUES ('Проверка', '', '', '', '', 0)")
    assert path.is_file()
    with Database(path, read_only=True) as reader:
        with reader.engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT full_name FROM employees").scalar() == "Проверка"
            with pytest.raises(OperationalError, match="readonly"):
                connection.exec_driver_sql("DELETE FROM employees")


def test_reader_does_not_create_missing_database(tmp_path):
    path = tmp_path / "missing" / "records.sqlite"
    with Database(path, read_only=True) as database:
        with pytest.raises(OperationalError):
            with database.engine.connect():
                pass
    assert not path.parent.exists()
