"""Archive operations owned by the daemon and serialized by its command lock."""

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
from uuid import uuid4

from certificate_analyzer.infrastructure.database.models import Base
from certificate_analyzer.infrastructure.persistence.notification_history import NotificationHistoryStore
from certificate_analyzer.infrastructure.transfer_archive import ArchiveError, _read, export_archive, import_archive

TABLES = ("employees", "certificates", "certificate_sources", "certificate_requests", "mchds", "mchd_authorities", "audit_events")


def _rows(connection, table):
    return [dict(row) for row in connection.execute(f'SELECT * FROM "{table}"')]


def _revision(data):
    canonical = {table: sorted((json.dumps(row, sort_keys=True, ensure_ascii=False) for row in rows)) for table, rows in data.items()}
    return hashlib.sha256(json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _employee_match(row, existing):
    for field in ("snils", "inn"):
        if row.get(field):
            matches = [item for item in existing if item.get(field) == row[field]]
            if len(matches) > 1:
                raise ArchiveError(f"Несколько сотрудников с одинаковым {field}; исправьте дубликаты")
            if matches:
                return matches[0]
    matches = [item for item in existing if (item.get("full_name") or "").strip().casefold() == (row.get("full_name") or "").strip().casefold() and (item.get("department") or "").strip().casefold() == (row.get("department") or "").strip().casefold()]
    if len(matches) > 1:
        raise ArchiveError("Неоднозначное совпадение сотрудника по ФИО и подразделению")
    return matches[0] if matches else None


class ArchiveService:
    def __init__(self, app):
        self.app = app

    def _writable(self):
        if self.app.database.read_only:
            raise ArchiveError("Импорт и экспорт выполняет фоновый процесс")

    def export_choices(self):
        self._writable()
        with closing(sqlite3.connect(self.app.database.path)) as connection:
            connection.row_factory = sqlite3.Row
            return {
                "certificates": [{"id": row["fingerprint_sha256"], "label": f"{row['subject']} — {row['original_name'] or row['fingerprint_sha256']}", "employee_id": row["employee_id"]} for row in _rows(connection, "certificates")],
                "employees": [{"id": row["id"], "label": f"{row['full_name']} — {row['department'] or 'Без подразделения'}"} for row in _rows(connection, "employees")],
                "mchds": [{"id": row["unified_number"], "label": f"{row['unified_number']} — {row['representative_fio']}"} for row in _rows(connection, "mchds")],
            }

    def export(self, destination, password, categories=None, record_ids=None):
        self._writable()
        categories = ["certificates", "employees", "mchds"] if categories is None else categories
        if not set(categories) <= {"certificates", "employees", "mchds"}:
            raise ArchiveError("Экспорт поддерживает сертификаты, сотрудников и МЧД")
        path = export_archive(self.app.database.path, self.app.certificates.storage.folder, Path(destination), password,
                              categories=categories, record_ids=record_ids, _writer_owned=True)
        return {"path": str(path)}

    def _restore(self, archive, password, parent):
        target = parent / uuid4().hex
        import_archive(Path(archive), target, password)
        return target

    def inspect(self, archive, password):
        self._writable()
        digest = hashlib.sha256(_read(Path(archive))).hexdigest()
        with tempfile.TemporaryDirectory(prefix="ca-preview-", dir=self.app.database.path.parent) as temp:
            profile = self._restore(archive, password, Path(temp))
            with closing(sqlite3.connect(profile / "certificates.db")) as incoming, closing(sqlite3.connect(self.app.database.path)) as current:
                incoming.row_factory = current.row_factory = sqlite3.Row
                employees = _rows(current, "employees")
                revision = _revision({table: _rows(current, table) for table in TABLES})
                requests = {row["request_number"]: row for row in _rows(current, "certificate_requests")}
                conflicts = []
                for row in _rows(incoming, "employees"):
                    match = _employee_match(row, employees)
                    if match and any(row.get(key) != match.get(key) for key in row if key != "id"):
                        conflicts.append({"key": f"employees:{row['id']}", "label": f"Сотрудник: {row['full_name']}", "current": match, "incoming": row})
                for row in _rows(incoming, "certificate_requests"):
                    match = requests.get(row["request_number"])
                    if match:
                        conflicts.append({"key": f"requests:{row['id']}", "label": f"Заявка: {row['request_number']}", "current": match, "incoming": row})
                if hashlib.sha256(_read(Path(archive))).hexdigest() != digest:
                    raise ArchiveError("Архив изменился во время проверки")
                return {"conflicts": conflicts, "counts": {table: len(_rows(incoming, table)) for table in TABLES}, "digest": digest, "revision": revision}

    def restore(self, archive, password, mode, decisions=None, expected_digest=None, expected_revision=None):
        self._writable()
        if mode not in {"add", "replace"}:
            raise ArchiveError("Выберите режим добавления или замены")
        decisions = decisions or {}
        if not isinstance(decisions, dict) or any(value not in {"current", "incoming", "skip"} for value in decisions.values()):
            raise ArchiveError("Некорректное разрешение конфликтов")
        imports = self.app.database.path.parent / "archive-imports"
        imports.mkdir(mode=0o700, exist_ok=True)
        profile = None
        backup_path = self.app.database.path.parent / ("before-import-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8] + ".cat")
        history_store = NotificationHistoryStore()
        old_history = history_store.load()
        history_changed = False
        try:
            if expected_digest and hashlib.sha256(_read(Path(archive))).hexdigest() != expected_digest:
                raise ArchiveError("Архив изменился; повторите просмотр конфликтов")
            profile = self._restore(archive, password, imports)
            if expected_digest and hashlib.sha256(_read(Path(archive))).hexdigest() != expected_digest:
                raise ArchiveError("Архив изменился во время импорта")
            # Full encrypted recovery copy is mandatory even for merge operations.
            export_archive(self.app.database.path, self.app.certificates.storage.folder, backup_path, password,
                           notification_history=old_history, _writer_owned=True)
            with closing(sqlite3.connect(profile / "certificates.db")) as incoming:
                incoming.row_factory = sqlite3.Row
                data = {table: _rows(incoming, table) for table in TABLES}
            with self.app.database.engine.begin() as transaction:
                if expected_revision:
                    current_data = {table: [dict(row) for row in transaction.exec_driver_sql(f'SELECT * FROM "{table}"').mappings()] for table in TABLES}
                    if _revision(current_data) != expected_revision:
                        raise ArchiveError("Текущие данные изменились; повторите просмотр конфликтов")
                if mode == "replace":
                    for table in reversed(TABLES):
                        transaction.exec_driver_sql(f'DELETE FROM "{table}"')
                existing_employees = [dict(row) for row in transaction.exec_driver_sql("SELECT * FROM employees").mappings()]
                employee_ids = {}
                added = {table: 0 for table in TABLES}

                def insert(table, row):
                    columns = {column.name for column in Base.metadata.tables[table].columns}
                    if not set(row) <= columns:
                        raise ArchiveError(f"Неизвестные поля в таблице {table}")
                    names = list(row)
                    result = transaction.exec_driver_sql(f'INSERT INTO "{table}" (' + ','.join(f'"{name}"' for name in names) + ') VALUES (' + ','.join('?' for _ in names) + ')', tuple(row[name] for name in names))
                    added[table] += 1
                    return result.lastrowid

                def update(table, row, field, identifier):
                    values = {key: value for key, value in row.items() if key != field}
                    if not set(values) <= {column.name for column in Base.metadata.tables[table].columns}:
                        raise ArchiveError("Неизвестные поля записи")
                    transaction.exec_driver_sql(f'UPDATE "{table}" SET ' + ','.join(f'"{key}"=?' for key in values) + f' WHERE "{field}"=?', tuple(values.values()) + (identifier,))

                for row in data["employees"]:
                    row = row.copy()
                    old_id = row.pop("id")
                    match = _employee_match(row, existing_employees) if mode == "add" else None
                    if match:
                        choice = decisions.get(f"employees:{old_id}")
                        differs = any(row.get(key) != match.get(key) for key in row)
                        if differs and choice is None:
                            raise ArchiveError("Данные изменились: повторите просмотр конфликтов сотрудников")
                        employee_ids[old_id] = match["id"]
                        if choice == "incoming":
                            update("employees", row, "id", match["id"])
                            match.update(row)
                    else:
                        new_id = insert("employees", row)
                        employee_ids[old_id] = new_id
                        existing_employees.append({**row, "id": new_id})
                for row in data["certificates"]:
                    row = row.copy()
                    row["employee_id"] = employee_ids.get(row.get("employee_id"))
                    exists = transaction.exec_driver_sql("SELECT source_path FROM certificates WHERE fingerprint_sha256=?", (row["fingerprint_sha256"],)).first()
                    if not exists:
                        insert("certificates", row)
                    elif not exists[0] or not Path(exists[0]).is_file():
                        transaction.exec_driver_sql("UPDATE certificates SET source_path=? WHERE fingerprint_sha256=?", (row["source_path"], row["fingerprint_sha256"]))
                for row in data["certificate_sources"]:
                    if not transaction.exec_driver_sql("SELECT 1 FROM certificate_sources WHERE fingerprint=? AND content_sha256=? AND file_name=?", (row["fingerprint"], row.get("content_sha256"), row.get("file_name"))).first():
                        insert("certificate_sources", row)
                for row in data["certificate_requests"]:
                    row = row.copy()
                    old_id = row.pop("id")
                    row["employee_id"] = employee_ids.get(row.get("employee_id"))
                    match = transaction.exec_driver_sql("SELECT id FROM certificate_requests WHERE request_number=?", (row["request_number"],)).first()
                    if match:
                        choice = decisions.get(f"requests:{old_id}")
                        if choice is None:
                            raise ArchiveError("Данные изменились: повторите просмотр конфликтов заявок")
                        if choice == "incoming":
                            update("certificate_requests", row, "id", match[0])
                    else:
                        insert("certificate_requests", row)
                new_mchds = set()
                for row in data["mchds"]:
                    if not transaction.exec_driver_sql("SELECT 1 FROM mchds WHERE unified_number=?", (row["unified_number"],)).first():
                        insert("mchds", row)
                        new_mchds.add(row["unified_number"])
                for row in data["mchd_authorities"]:
                    if row["mchd_number"] in new_mchds:
                        insert("mchd_authorities", {key: value for key, value in row.items() if key != "id"})
                audit_fields = [column.name for column in Base.metadata.tables["audit_events"].columns if column.name != "id"]
                seen_events = {tuple(row[field] for field in audit_fields) for row in transaction.exec_driver_sql("SELECT * FROM audit_events").mappings()}
                for row in data["audit_events"]:
                    signature = tuple(row[field] for field in audit_fields)
                    if signature not in seen_events:
                        insert("audit_events", {key: value for key, value in row.items() if key != "id"})
                        seen_events.add(signature)
                if transaction.exec_driver_sql("PRAGMA foreign_key_check").first():
                    raise ArchiveError("Импорт нарушает связи данных")
                history_file = profile / "notification_history.json"
                if history_file.exists():
                    imported_history = json.loads(history_file.read_text(encoding="utf-8"))
                    combined = imported_history if mode == "replace" else imported_history + old_history
                    unique = []
                    for item in combined:
                        if item not in unique:
                            unique.append(item)
                    history_changed = True
                    history_store.save(unique)
            # Keep the profile intact after commit; no fallible cleanup may roll
            # back files referenced by the now-committed database.
            return {"backup": str(backup_path), "added": added, "mode": mode}
        except BaseException:
            if history_changed:
                history_store.save(old_history)
            if profile is not None:
                shutil.rmtree(profile)
            raise
