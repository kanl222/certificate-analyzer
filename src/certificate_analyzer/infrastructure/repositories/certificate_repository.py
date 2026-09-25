"""Metadata repository using short SQLAlchemy sessions and batched upserts."""

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, delete, func, or_, select
from sqlalchemy.dialects.sqlite import insert

from certificate_analyzer.application.dto.certificate_query import CertificateQuery
from certificate_analyzer.domain.enums.certificate_status import CertificateStatus
from certificate_analyzer.domain.models.certificate import Certificate
from certificate_analyzer.domain.models.employee import Employee
from certificate_analyzer.domain.services.certificate_status import utc
from certificate_analyzer.infrastructure.database.models.certificates import (
    CertificateModel as Model,
    CertificateSourceModel as Source,
)


class CertificateRepository:
    def __init__(self, session_factory, warning_days=60):
        self.sessions = session_factory
        self.warning_days = warning_days

    def _status(self, now=None):
        now = utc(now or datetime.now(timezone.utc)).replace(tzinfo=None)
        return case(
            (Model.status == "REVOKED", "REVOKED"),
            (or_(Model.valid_to < Model.valid_from, Model.valid_from > now), "INVALID"),
            (Model.valid_to <= now, "EXPIRED"),
            (
                Model.valid_to <= now + timedelta(days=self.warning_days),
                "EXPIRING_SOON",
            ),
            else_="ACTIVE",
        )

    @staticmethod
    def _values(cert):
        employee = cert.employee
        values = dict(
            fingerprint_sha256=cert.fingerprint_sha256,
            subject=cert.subject,
            issuer=cert.issuer,
            valid_from=utc(cert.valid_from).replace(tzinfo=None),
            valid_to=utc(cert.valid_to).replace(tzinfo=None),
            status=cert.status.value,
            serial_number=cert.serial_number,
            has_private_key_link=cert.has_private_key_link,
            owner_name=cert.owner_name,
            source_path=cert.source_path,
            email=cert.email,
            office=employee.office or "" if employee else "",
            department=employee.department or "" if employee else "",
            phones_json=json.dumps(
                employee.phones if employee else [], ensure_ascii=False
            ),
            original_name=cert.original_name,
        )
        values["search_text"] = " ".join(
            str(v or "")
            for k, v in values.items()
            if k not in ("valid_from", "valid_to")
        ).casefold()
        return values

    def save_many(self, certificates, sources=()):
        values = [self._values(cert) for cert in certificates]
        if not values and not sources:
            return 0
        with self.sessions.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            inserted = 0
            if values:
                keys = list(dict.fromkeys(v["fingerprint_sha256"] for v in values))
                known = set(
                    session.scalars(
                        select(Model.fingerprint_sha256).where(
                            Model.fingerprint_sha256.in_(keys)
                        )
                    )
                )
                inserted = len(set(keys) - known)
                statement = insert(Model)
                updates = {
                    key: getattr(statement.excluded, key)
                    for key in values[0]
                    if key != "fingerprint_sha256"
                }
                updates["status"] = case(
                    (Model.status == "REVOKED", "REVOKED"),
                    else_=statement.excluded.status,
                )
                updates["phones_json"] = case(
                    (statement.excluded.phones_json == "[]", Model.phones_json),
                    else_=statement.excluded.phones_json,
                )
                updates["original_name"] = case(
                    (Model.original_name != "", Model.original_name),
                    else_=statement.excluded.original_name,
                )
                updates["search_text"] = (
                    statement.excluded.search_text
                    + " "
                    + updates["phones_json"]
                    + " "
                    + updates["original_name"]
                )
                session.execute(
                    statement.on_conflict_do_update(
                        index_elements=["fingerprint_sha256"], set_=updates
                    ),
                    values,
                )
            if sources:
                statement = insert(Source)
                session.execute(
                    statement.on_conflict_do_update(
                        index_elements=["path"],
                        set_={
                            "fingerprint": statement.excluded.fingerprint,
                            "content_sha256": statement.excluded.content_sha256,
                        },
                    ),
                    list(sources),
                )
        return inserted

    def save(self, certificate):
        return self.save_many([certificate])

    def cached_sources(self, paths):
        with self.sessions() as session:
            rows = session.execute(
                select(
                    Source.path,
                    Source.content_sha256,
                    Model.source_path,
                    Source.fingerprint,
                )
                .join(Model, Model.fingerprint_sha256 == Source.fingerprint)
                .where(Source.path.in_(paths))
            )
            return {
                path: (digest, stored_path, fingerprint)
                for path, digest, stored_path, fingerprint in rows
            }

    def find_many(self, fingerprints):
        with self.sessions() as session:
            rows = session.execute(
                select(Model, self._status()).where(
                    Model.fingerprint_sha256.in_(fingerprints)
                )
            )
            return [self._to_domain(*row) for row in rows]

    def _where(self, query, status):
        conditions = []
        if query.search.strip():
            conditions.append(
                Model.search_text.contains(
                    query.search.strip().casefold(), autoescape=True
                )
            )
        if query.status:
            conditions.append(status == CertificateStatus(query.status).value)
        if query.date_from:
            conditions.append(
                Model.valid_to >= datetime.combine(query.date_from, datetime.min.time())
            )
        if query.date_to:
            conditions.append(
                Model.valid_to
                < datetime.combine(
                    query.date_to + timedelta(days=1), datetime.min.time()
                )
            )
        return conditions

    def list(self, query=None, now=None):
        query = query or CertificateQuery()
        status = self._status(now)
        columns = {
            "subject": Model.subject,
            "valid_to": Model.valid_to,
            "valid_from": Model.valid_from,
            "issuer": Model.issuer,
            "status": status,
            "original_name": Model.original_name,
            "department": Model.department,
            "serial_number": Model.serial_number,
        }
        if query.sort not in columns:
            raise ValueError("Неизвестное поле сортировки")
        order = columns[query.sort]
        statement = select(Model, status.label("current_status")).where(
            *self._where(query, status)
        )
        statement = statement.order_by(
            order.desc() if query.descending else order.asc(), Model.fingerprint_sha256
        ).offset(query.offset)
        if query.limit is not None:
            statement = statement.limit(query.limit)
        with self.sessions() as session:
            return [
                self._to_domain(model, current)
                for model, current in session.execute(statement)
            ]

    def get_all(self):
        return self.list(CertificateQuery(limit=None))

    def statistics(self, query=None, now=None):
        query = query or CertificateQuery()
        status = self._status(now)
        with self.sessions() as session:
            counts = dict(
                session.execute(
                    select(status, func.count())
                    .select_from(Model)
                    .where(*self._where(query, status))
                    .group_by(status)
                ).all()
            )
        return {
            "total": sum(counts.values()),
            **{item.value: counts.get(item.value, 0) for item in CertificateStatus},
        }

    def find_by_fingerprint(self, fingerprint):
        with self.sessions() as session:
            row = session.execute(
                select(Model, self._status()).where(
                    Model.fingerprint_sha256 == fingerprint
                )
            ).first()
            return self._to_domain(*row) if row else None

    def delete(self, fingerprints):
        with self.sessions.begin() as session:
            result = session.execute(
                delete(Model).where(Model.fingerprint_sha256.in_(fingerprints))
            )
            return result.rowcount

    @staticmethod
    def _to_domain(model, status):
        return Certificate(
            fingerprint_sha256=model.fingerprint_sha256,
            subject=model.subject,
            issuer=model.issuer,
            valid_from=utc(model.valid_from),
            valid_to=utc(model.valid_to),
            status=CertificateStatus(status),
            serial_number=model.serial_number,
            has_private_key_link=model.has_private_key_link,
            owner_name=model.owner_name,
            source_path=model.source_path or "",
            email=model.email,
            original_name=model.original_name,
            employee=Employee(
                full_name=model.owner_name or model.subject,
                office=model.office or None,
                department=model.department or None,
                phones=json.loads(model.phones_json),
            ),
        )
