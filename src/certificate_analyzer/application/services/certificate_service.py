from dataclasses import dataclass, field
from pathlib import Path

from certificate_analyzer.domain.enums.certificate_status import CertificateStatus
from certificate_analyzer.domain.services.certificate_status import certificate_status


@dataclass
class CertificateScanResult:
    certificates: list = field(default_factory=list)
    expired: list = field(default_factory=list)
    expiring: list = field(default_factory=list)
    active: list = field(default_factory=list)
    errors: dict = field(default_factory=dict)
    loaded_files: list = field(default_factory=list)


class CertificateService:
    """Application service для работы с сертификатами."""

    def __init__(
        self,
        *,
        scanner,
        parser,
        repository,
        phonebook_service,
        settings,
    ) -> None:
        self._scanner = scanner
        self._parser = parser
        self._repository = repository
        self._phonebook = phonebook_service
        self._settings = settings

    def scan(
        self,
        folder: str | Path,
    ) -> CertificateScanResult:
        result = CertificateScanResult()

        files = self._scanner.scan(folder)
        result.loaded_files = [str(f) for f in files]

        for path in files:
            try:
                certificate = self._parse(path)
                certificate.source_path = str(path)

                self._repository.save(
                    certificate
                )

            except (OSError, ValueError) as exc:
                result.errors[Path(path)] = str(exc)
                continue

            result.certificates.append(
                certificate
            )

            match certificate.status:
                case CertificateStatus.EXPIRED:
                    result.expired.append(
                        certificate
                    )

                case CertificateStatus.EXPIRING_SOON:
                    result.expiring.append(
                        certificate
                    )

                case CertificateStatus.ACTIVE:
                    result.active.append(
                        certificate
                    )

        return result

    def _parse(
        self,
        path: str | Path,
    ):
        certificate = self._parser.parse(path)

        certificate.status = certificate_status(
            certificate.valid_from,
            certificate.valid_to,
            warning_days=self._settings.warning_days,
        )

        self._enrich_employee(
            certificate
        )

        return certificate

    def _enrich_employee(
        self,
        certificate,
    ) -> None:
        employee = certificate.employee

        if employee is None:
            return

        phone = self._phonebook.find_phone(
            office=employee.office,
            full_name=employee.full_name,
            department=employee.department,
        )

        if (
            phone
            and phone != "—"
            and phone not in employee.phones
        ):
            employee.phones.append(phone)


class CertificateAnalyzerCore:
    """Backward-compatible facade used by tests and the legacy presenter.

    Wraps the standalone scanner and parser without requiring DI wiring.
    """

    def __init__(self, settings) -> None:
        from certificate_analyzer.infrastructure.certificates.scanner import scan_files
        from certificate_analyzer.infrastructure.certificates.x509_parser import X509Parser

        self._settings = settings
        self._scan_files = scan_files
        self._parser = X509Parser

        self._scanned_paths: list[Path] = []
        self.certificates: list = []
        self.errors: dict = {}
        self.expired_certs: list = []
        self.loaded_files: list[str] = []
        self.cert_stats: dict = {
            "total": 0,
            "expired": 0,
            "expiring": 0,
            "active": 0,
        }
        self.phonebook = None

    def scan_certificates(self, folder: str | Path) -> None:
        """Scan folder and store found paths; clears previous state."""
        self.certificates = []
        self.errors = {}
        self.expired_certs = []
        self.loaded_files = []
        self.cert_stats = {"total": 0, "expired": 0, "expiring": 0, "active": 0}

        try:
            self._scanned_paths = self._scan_files(folder)
        except (FileNotFoundError, NotADirectoryError):
            self._scanned_paths = []
        self.loaded_files = [str(p) for p in self._scanned_paths]

    def parse_certificates(self) -> list:
        """Parse all previously scanned paths and return view-ready list."""
        self.certificates = []
        self.errors = {}
        self.expired_certs = []

        for path in self._scanned_paths:
            try:
                cert = self._parser.parse(path)
                cert.status = certificate_status(
                    cert.valid_from,
                    cert.valid_to,
                    warning_days=self._settings.warning_days,
                )
                cert.source_path = str(path)
                self.certificates.append(cert)

                match cert.status:
                    case CertificateStatus.EXPIRED:
                        self.expired_certs.append(cert)
                    case _:
                        pass

            except (OSError, ValueError) as exc:
                self.errors[path] = str(exc)

        self.cert_stats = {
            "total": len(self.certificates),
            "expired": sum(
                1 for c in self.certificates if c.status == CertificateStatus.EXPIRED
            ),
            "expiring": sum(
                1 for c in self.certificates if c.status == CertificateStatus.EXPIRING_SOON
            ),
            "active": sum(
                1 for c in self.certificates if c.status == CertificateStatus.ACTIVE
            ),
        }
        return self.certificates

    def load_phonebook(self, file_path: str) -> bool:
        """Load phonebook from file. Returns True on success."""
        from certificate_analyzer.application.services.phonebook_service import PhoneBook

        try:
            pb = PhoneBook()
            pb.load(file_path)
            self.phonebook = pb
            return True
        except Exception:  # noqa: BLE001
            return False

    def export_to_excel(self, data: list, save_path: str, title: str) -> str | None:
        """Export data rows to Excel. Returns save_path on success."""
        from certificate_analyzer.infrastructure.reports.excel_exporter import ExcelReportExporter

        try:
            ExcelReportExporter().export_rows(data, save_path, title)
            return save_path
        except Exception:  # noqa: BLE001
            return None

    def export_to_pdf(
        self,
        data: list,
        save_path: str,
        figure,
        title: str,
        include_chart: bool = True,
    ) -> str | None:
        """Export data rows to PDF. Returns save_path on success."""
        from certificate_analyzer.infrastructure.reports.pdf_exporter import PdfReportExporter

        try:
            PdfReportExporter().export(data, save_path, figure, title, include_chart)
            return save_path
        except Exception:  # noqa: BLE001
            return None