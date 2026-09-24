from dataclasses import dataclass

from certificate_analyzer.application.services.certificate_service import (
    CertificateService,
)
from certificate_analyzer.application.services.phonebook_service import PhoneBook
from certificate_analyzer.infrastructure.certificates.scanner import scan_files
from certificate_analyzer.infrastructure.certificates.x509_parser import X509Parser
from certificate_analyzer.infrastructure.config.config_loader import load_settings
from certificate_analyzer.infrastructure.config.settings import Settings
from certificate_analyzer.infrastructure.database.session import SessionLocal, init_db
from certificate_analyzer.infrastructure.repositories.certificate_repository import (
    CertificateRepository,
)


class DummyScanner:
    def scan(self, folder):
        return scan_files(folder)

@dataclass
class ApplicationContainer:
    settings: Settings
    certificates: CertificateService


def create_application(config_path=None):
    settings = load_settings(config_path)
    init_db()
    db_session = SessionLocal()
    cert_repo = CertificateRepository(db_session)
    phonebook = PhoneBook()
    
    cert_service = CertificateService(
        scanner=DummyScanner(),
        parser=X509Parser,
        repository=cert_repo,
        phonebook_service=phonebook,
        settings=settings
    )
    
    return ApplicationContainer(settings, cert_service)
