"""Аддитивные миграции схемы базы данных SQLite."""

import json
from pathlib import Path
import sqlite3
from datetime import datetime, timezone

SCHEMA_VERSION = 4



def migrate(engine, path):
    """Выполняет последовательные аддитивные миграции структуры SQLite-базы данных.

    Args:
        engine: Экземпляр SQLAlchemy Engine.
        path: Путь к файлу базы данных SQLite.

    Raises:
        ValueError: Если версия базы данных новее версии приложения.
    """
    with engine.connect() as connection:
        version = connection.exec_driver_sql("PRAGMA user_version").scalar() or 0
        if version > SCHEMA_VERSION:
            raise ValueError("Версия базы новее приложения")
        if version == SCHEMA_VERSION:
            return
        tables = set(
            connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).scalars()
        )

    if "certificates" in tables:
        backup = path.with_name(
            path.name + datetime.now(timezone.utc).strftime(".%Y%m%d%H%M%S%f.bak")
        )
        # SQLite backup API копирует консистентный снимок данных, включая журнал WAL
        with sqlite3.connect(path) as source, sqlite3.connect(backup) as destination:
            source.backup(destination)

    with engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            current_version = connection.exec_driver_sql("PRAGMA user_version").scalar() or 0
            if current_version == SCHEMA_VERSION:
                connection.commit()
                return

            if current_version < 1 and "certificates" in tables:
                columns = {
                    r[1]
                    for r in connection.exec_driver_sql(
                        "PRAGMA table_info(certificates)"
                    )
                }
                for name, definition in {
                    "email": "TEXT NOT NULL DEFAULT ''",
                    "office": "TEXT NOT NULL DEFAULT ''",
                    "department": "TEXT NOT NULL DEFAULT ''",
                    "phones_json": "TEXT NOT NULL DEFAULT '[]'",
                    "original_name": "TEXT NOT NULL DEFAULT ''",
                    "search_text": "TEXT NOT NULL DEFAULT ''",
                }.items():
                    if name not in columns:
                        connection.exec_driver_sql(
                            f"ALTER TABLE certificates ADD COLUMN {name} {definition}"
                        )
                if "employees" in tables and "employee_id" in columns:
                    rows = connection.exec_driver_sql("""SELECT c.fingerprint_sha256, e.email, e.office, e.department, e.phones
                        FROM certificates c JOIN employees e ON c.employee_id=e.id""").all()
                    for fingerprint, email, office, department, phones in rows:
                        connection.exec_driver_sql(
                            """UPDATE certificates SET email=?, office=?, department=?, phones_json=?
                            WHERE fingerprint_sha256=?""",
                            (
                                email or "",
                                office or "",
                                department or "",
                                json.dumps(
                                    [
                                        p.strip()
                                        for p in (phones or "").split(",")
                                        if p.strip()
                                    ],
                                    ensure_ascii=False,
                                ),
                                fingerprint,
                            ),
                        )
                rows = connection.exec_driver_sql(
                    "SELECT fingerprint_sha256, subject, issuer, serial_number, email, office, department, phones_json, source_path FROM certificates"
                ).all()
                for row in rows:
                    connection.exec_driver_sql(
                        "UPDATE certificates SET search_text=?, original_name=? WHERE fingerprint_sha256=?",
                        (
                            " ".join(str(v or "") for v in row).casefold(),
                            Path(row[-1] or "").name,
                            row[0],
                        ),
                    )
                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_certificates_valid_to ON certificates(valid_to)"
                )
                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_certificates_subject ON certificates(subject)"
                )

            if current_version < 2 and "employees" in tables:
                emp_cols = {
                    r[1]
                    for r in connection.exec_driver_sql(
                        "PRAGMA table_info(employees)"
                    )
                }
                for name, definition in {
                    "position": "VARCHAR(255)",
                    "inn": "VARCHAR(20)",
                    "snils": "VARCHAR(20)",
                    "birth_date": "DATE",
                }.items():
                    if name not in emp_cols:
                        connection.exec_driver_sql(
                            f"ALTER TABLE employees ADD COLUMN {name} {definition}"
                        )

            if current_version < 3:
                if "certificate_sources" in tables:
                    source_cols = {
                        r[1]
                        for r in connection.exec_driver_sql(
                            "PRAGMA table_info(certificate_sources)"
                        )
                    }
                    for name, definition in {
                        "file_name": "VARCHAR(255) DEFAULT ''",
                        "size": "INTEGER DEFAULT 0",
                        "first_seen_at": "TIMESTAMP",
                        "last_seen_at": "TIMESTAMP",
                    }.items():
                        if name not in source_cols:
                            connection.exec_driver_sql(
                                f"ALTER TABLE certificate_sources ADD COLUMN {name} {definition}"
                            )
                connection.exec_driver_sql(
                    """CREATE TABLE IF NOT EXISTS audit_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type VARCHAR(50) NOT NULL,
                        entity_type VARCHAR(50) NOT NULL,
                        entity_id VARCHAR(255) NOT NULL,
                        description TEXT NOT NULL,
                        details_json TEXT NOT NULL DEFAULT '{}',
                        created_at TIMESTAMP NOT NULL
                    )"""
                )
                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_audit_events_event_type ON audit_events(event_type)"
                )
                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_audit_events_entity_type ON audit_events(entity_type)"
                )
                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_audit_events_entity_id ON audit_events(entity_id)"
                )
                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_audit_events_created_at ON audit_events(created_at)"
                )

            if current_version < 4:
                connection.exec_driver_sql(
                    """CREATE TABLE IF NOT EXISTS mchd_authorities (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        mchd_number VARCHAR(255) NOT NULL,
                        code VARCHAR(100) NOT NULL,
                        name VARCHAR(500),
                        FOREIGN KEY (mchd_number) REFERENCES mchds(unified_number) ON DELETE CASCADE
                    )"""
                )
                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_mchd_authorities_mchd_number ON mchd_authorities(mchd_number)"
                )
                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_mchd_authorities_code ON mchd_authorities(code)"
                )
                if "mchds" in tables:
                    rows = connection.exec_driver_sql(
                        "SELECT unified_number, authority_codes FROM mchds WHERE authority_codes IS NOT NULL AND authority_codes != ''"
                    ).all()
                    for num, raw_codes in rows:
                        codes = [c.strip() for c in (raw_codes or "").split(",") if c.strip()]
                        for code in codes:
                            connection.exec_driver_sql(
                                "INSERT INTO mchd_authorities (mchd_number, code, name) VALUES (?, ?, ?)",
                                (num, code, None),
                            )

            connection.exec_driver_sql(f"PRAGMA user_version={SCHEMA_VERSION}")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
