"""One application service for imports and database-backed certificate queries."""

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

from certificate_analyzer.application.dto.certificate_query import CertificateQuery
from certificate_analyzer.domain.models.certificate import Certificate
from certificate_analyzer.domain.services.certificate_status import certificate_status


@dataclass
class ImportResult:
    certificates: list[Certificate] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)
    imported: int = 0
    updated: int = 0
    skipped: int = 0


class CertificateService:
    def __init__(
        self, *, scanner, parser, repository, storage, phonebook_service, settings
    ):
        self.scanner = scanner
        self.parser = parser
        self.repository = repository
        self.storage = storage
        self.phonebook = phonebook_service
        self.settings = settings

    def import_folder(self, folder, phonebook_path=None):
        return self.import_files(self.scanner(folder), phonebook_path=phonebook_path)

    def import_files(self, paths, phonebook_path=None):
        result = ImportResult()
        if phonebook_path:
            self.phonebook.load(phonebook_path)
        elif self.settings.phonebook_path and not self.phonebook.employees:
            try:
                self.phonebook.load(self.settings.phonebook_path)
            except (OSError, ValueError) as exc:
                result.errors[str(self.settings.phonebook_path)] = str(exc)
        paths = list(dict.fromkeys(str(Path(p).expanduser().resolve()) for p in paths))
        collected = {}
        # Bound SQL parameter counts and transaction duration for large imports.
        for start in range(0, len(paths), 200):
            batch = paths[start : start + 200]
            known = self.repository.cached_sources(batch)
            certificates, sources, fingerprints = [], [], []
            for path in batch:
                try:
                    data = Path(path).read_bytes()
                    digest = sha256(data).hexdigest()
                    cached = known.get(path)
                    if cached and cached[0] == digest and not self.phonebook.employees:
                        stored = Path(cached[1])
                        if (
                            stored.parent == self.storage.folder
                            and stored.is_file()
                            and sha256(stored.read_bytes()).hexdigest().upper()
                            == cached[2]
                        ):
                            result.skipped += 1
                            fingerprints.append(cached[2])
                            continue
                    cert, der = self.parser.parse_for_import(data)
                    cert.status = certificate_status(
                        cert.valid_from,
                        cert.valid_to,
                        warning_days=self.settings.warning_days,
                    )
                    cert.original_name = Path(path).name
                    cert.source_path = str(
                        self.storage.put(cert.fingerprint_sha256, der)
                    )
                    self._enrich(cert)
                    certificates.append(cert)
                    sources.append(
                        {
                            "path": path,
                            "fingerprint": cert.fingerprint_sha256,
                            "content_sha256": digest,
                        }
                    )
                    fingerprints.append(cert.fingerprint_sha256)
                except (ValueError, OSError) as exc:
                    result.errors[path] = str(exc)
            inserted = self.repository.save_many(certificates, sources)
            result.imported += inserted
            result.updated += len(certificates) - inserted
            for cert in self.repository.find_many(list(dict.fromkeys(fingerprints))):
                collected[cert.fingerprint_sha256] = cert
        result.certificates = list(collected.values())
        return result

    def _enrich(self, cert):
        if not cert.employee:
            return
        phone = self.phonebook.find_phone(
            office=cert.employee.office,
            full_name=cert.employee.full_name,
            department=cert.employee.department,
        )
        if phone:
            cert.employee.phones = [p.strip() for p in phone.split(",") if p.strip()]

    def load_phonebook(self, path):
        self.phonebook.load(path)
        # Enrich existing records without rereading certificate files.
        offset = 0
        while batch := self.repository.list(CertificateQuery(limit=200, offset=offset)):
            for cert in batch:
                self._enrich(cert)
            self.repository.save_many(batch)
            offset += len(batch)
        return len(self.phonebook.employees)

    def list(self, query=None):
        return self.repository.list(query)

    def statistics(self, query=None):
        return self.repository.statistics(query)

    def get(self, fingerprint):
        cert = self.repository.find_by_fingerprint(fingerprint)
        if cert is None:
            raise ValueError("Запись сертификата не найдена")
        return cert

    def delete_records(self, fingerprints):
        # Explicitly remove metadata only. Managed files can be reimported.
        return self.repository.delete(fingerprints)
