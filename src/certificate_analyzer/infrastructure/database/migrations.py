"""Additive migrations for the existing SQLAlchemy tables."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1


def migrate(engine, path):
    with engine.connect() as connection:
        version = connection.exec_driver_sql("PRAGMA user_version").scalar()
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
        # SQLite backup API copies a consistent snapshot, including WAL.
        with sqlite3.connect(path) as source, sqlite3.connect(backup) as destination:
            source.backup(destination)
    with engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            # Another process may have migrated while we waited for the lock.
            if (
                connection.exec_driver_sql("PRAGMA user_version").scalar()
                == SCHEMA_VERSION
            ):
                connection.commit()
                return
            if "certificates" in tables:
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
            connection.exec_driver_sql(f"PRAGMA user_version={SCHEMA_VERSION}")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
