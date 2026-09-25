"""Композиционный корень (Composition Root) и контейнер приложения."""

from dataclasses import dataclass

from certificate_analyzer.application.services.audit_service import AuditService
from certificate_analyzer.application.services.certificate_request_service import (
    CertificateRequestService,
)
from certificate_analyzer.application.services.certificate_service import (
    CertificateService,
)
from certificate_analyzer.application.services.employee_service import EmployeeService
from certificate_analyzer.application.services.mchd_service import MchdService
from certificate_analyzer.application.services.notification_service import (
    PushNotificationManager,
)
from certificate_analyzer.application.services.phonebook_service import PhoneBook
from certificate_analyzer.application.services.report_service import ReportService
from certificate_analyzer.infrastructure.certificates.scanner import scan_files
from certificate_analyzer.infrastructure.certificates.storage import CertificateStorage
from certificate_analyzer.infrastructure.certificates.x509_parser import X509Parser
from certificate_analyzer.infrastructure.config.config_loader import load_settings
from certificate_analyzer.infrastructure.config.paths import config_dir
from certificate_analyzer.infrastructure.config.settings import Settings
from certificate_analyzer.infrastructure.database.session import (
    Database,
    get_database_path,
)
from certificate_analyzer.infrastructure.platform.base import (
    PlatformFileManager,
    get_platform_file_manager,
)
from certificate_analyzer.infrastructure.repositories.audit_repository import (
    AuditRepository,
)
from certificate_analyzer.infrastructure.repositories.certificate_file_repository import (
    CertificateFileRepository,
)
from certificate_analyzer.infrastructure.repositories.certificate_repository import (
    CertificateRepository,
)
from certificate_analyzer.infrastructure.repositories.certificate_request_repository import (
    CertificateRequestRepository,
)
from certificate_analyzer.infrastructure.repositories.employee_repository import (
    EmployeeRepository,
)


@dataclass
class ApplicationContainer:
    """Контейнер зависимостей и сервисов приложения."""

    settings: Settings
    database: Database
    certificates: CertificateService
    reports: ReportService
    mchds: MchdService
    notifications: PushNotificationManager | None = None
    platform: PlatformFileManager | None = None
    certificate_requests: CertificateRequestService | None = None
    employees: EmployeeService | None = None
    audit: AuditService | None = None
    certificate_files: CertificateFileRepository | None = None

    def close(self) -> None:
        """Освобождает занятые ресурсы и закрывает соединение с базой данных."""
        self.database.close()

    def __enter__(self) -> "ApplicationContainer":
        """Вход в контекстный менеджер контейнера приложения."""
        return self

    def __exit__(self, *_) -> None:
        """Выход из контекстного менеджера с гарантированным освобождением ресурсов."""
        self.close()


def create_application(config_path=None, *, settings=None) -> ApplicationContainer:
    """Создает и настраивает экземпляр контейнера приложения.

    Args:
        config_path: Путь к файлу конфигурации (опционально).
        settings: Готовый экземпляр настроек Settings (опционально).

    Returns:
        ApplicationContainer: Сконфигурированный контейнер приложения.

    Raises:
        Exception: При ошибке инициализации базы данных или сервисов.
    """
    settings = settings or load_settings(config_path)
    database = Database(get_database_path(settings))
    try:
        phonebook = PhoneBook()
        repository = CertificateRepository(database.sessions, settings.warning_days)
        storage_folder = settings.storage_folder or config_dir() / "certificates"
        platform = get_platform_file_manager()
        audit_repo = AuditRepository(database.sessions)
        audit_service = AuditService(audit_repo)
        file_repo = CertificateFileRepository(database.sessions)
        employee_repo = EmployeeRepository(database.sessions)
        employee_service = EmployeeService(employee_repo)

        certificates = CertificateService(
            scanner=scan_files,
            parser=X509Parser,
            repository=repository,
            storage=CertificateStorage(storage_folder),
            phonebook_service=phonebook,
            settings=settings,
            platform_file_manager=platform,
            audit_service=audit_service,
            file_repository=file_repo,
            employee_service=employee_service,
        )
        reports = ReportService()
        mchds = MchdService()
        notifications = PushNotificationManager()
        request_repo = CertificateRequestRepository(database.sessions)
        request_service = CertificateRequestService(request_repo, employee_repo)

        return ApplicationContainer(
            settings=settings,
            database=database,
            certificates=certificates,
            reports=reports,
            mchds=mchds,
            notifications=notifications,
            platform=platform,
            certificate_requests=request_service,
            employees=employee_service,
            audit=audit_service,
            certificate_files=file_repo,
        )
    except Exception:
        database.close()
        raise
