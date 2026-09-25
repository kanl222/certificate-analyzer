from dataclasses import dataclass

from certificate_analyzer.application.services.certificate_service import (
    CertificateService,
)
from certificate_analyzer.application.services.phonebook_service import PhoneBook
from certificate_analyzer.application.services.report_service import ReportService
from certificate_analyzer.application.services.mchd_service import MchdService
from certificate_analyzer.infrastructure.certificates.scanner import scan_files
from certificate_analyzer.infrastructure.certificates.x509_parser import X509Parser
from certificate_analyzer.infrastructure.certificates.storage import CertificateStorage
from certificate_analyzer.infrastructure.config.config_loader import load_settings
from certificate_analyzer.infrastructure.config.paths import config_dir
from certificate_analyzer.infrastructure.config.settings import Settings
from certificate_analyzer.infrastructure.database.session import (
    Database,
    get_database_path,
)
from certificate_analyzer.infrastructure.repositories.certificate_repository import (
    CertificateRepository,
)


@dataclass
class ApplicationContainer:
    settings: Settings
    database: Database
    certificates: CertificateService
    reports: ReportService
    mchds: MchdService

    def close(self):
        self.database.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def create_application(config_path=None, *, settings=None):
    settings = settings or load_settings(config_path)
    database = Database(get_database_path(settings))
    try:
        phonebook = PhoneBook()
        repository = CertificateRepository(database.sessions, settings.warning_days)
        certificates = CertificateService(
            scanner=scan_files,
            parser=X509Parser,
            repository=repository,
            storage=CertificateStorage(
                settings.storage_folder or config_dir() / "certificates"
            ),
            phonebook_service=phonebook,
            settings=settings,
        )
        return ApplicationContainer(
            settings, database, certificates, ReportService(), MchdService()
        )
    except Exception:
        database.close()
        raise
