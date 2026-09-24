from pathlib import Path
from certificate_analyzer.application.dto.certificate_dto import certificate_to_dict
from certificate_analyzer.application.services.phonebook_service import PhoneBook
from certificate_analyzer.domain.enums.certificate_status import CertificateStatus
from certificate_analyzer.domain.services.certificate_status import certificate_status
from certificate_analyzer.infrastructure.certificates.scanner import scan_files
from certificate_analyzer.infrastructure.certificates.x509_parser import X509Parser
from certificate_analyzer.infrastructure.config.config_loader import load_settings


class CertificateAnalyzerCore:
    """Application facade shared by GUI, CLI and monitoring."""

    def __init__(self, settings=None):
        from certificate_analyzer.infrastructure.database.session import init_db, SessionLocal
        from certificate_analyzer.infrastructure.repositories.certificate_repository import CertificateRepository
        
        init_db()
        self.db_session = SessionLocal()
        self.cert_repo = CertificateRepository(self.db_session)
        
        self.settings = settings or load_settings()
        self.loaded_files = []
        self.current_folder = ""
        self.export_folder = self.settings.export_folder
        self.mchd_folder = self.settings.mchd_folder
        self.phonebook = PhoneBook()
        self.certificates = []
        self.errors = {}
        self.cert_stats = {"expired": 0, "warning": 0, "normal": 0}
        self.expired_certs = []
        self.warning_certs = []
        if self.settings.phonebook_path:
            self.load_phonebook(self.settings.phonebook_path)

    def __del__(self):
        if hasattr(self, 'db_session'):
            self.db_session.close()

    def load_phonebook(self, file_path):
        return self.phonebook.load(file_path)

    def get_phone_for_cert(self, cert_info):
        return self.phonebook.get_phone_for_cert(cert_info)

    def scan_certificates(self, folder_path=None):
        self.current_folder = str(
            folder_path
            or next(iter(self.settings.folders.values()), Path.home() / "Certs")
        )
        self.loaded_files = scan_files(self.current_folder)
        return self.loaded_files

    def scan_mchd_files(self, folder_path=None):
        folder = folder_path or self.mchd_folder
        return scan_files(folder, (".xml",)) if Path(folder).is_dir() else []

    def parse_model(self, path):
        cert = X509Parser.parse(path)
        cert.status = certificate_status(
            cert.valid_from, cert.valid_to, warning_days=self.settings.warning_days
        )
        
        # UI/DTO extraction should technically be moved out, 
        # but for now we attach phone to the employee if it exists
        if cert.employee:
            phone = self.get_phone_for_cert({"name": cert.employee.full_name, "office": cert.employee.office, "department": cert.employee.department})
            if phone and phone != "—":
                cert.employee.phones.append(phone)
                
        return cert

    def extract_certificate_info(self, cert_path):
        try:
            return certificate_to_dict(self.parse_model(cert_path))
        except (ValueError, OSError) as exc:
            return {"error": str(exc), "file_name": str(cert_path)}

    def parse_certificates(self):
        self.certificates = []
        self.errors = {}
        self.cert_stats = {"expired": 0, "warning": 0, "normal": 0}
        self.expired_certs, self.warning_certs = [], []
        results = []
        for path in self.loaded_files:
            try:
                cert = self.parse_model(path)
                self.cert_repo.save(cert)
            except (ValueError, OSError) as exc:
                self.errors[str(path)] = str(exc)
                continue
            self.certificates.append(cert)
            row = certificate_to_dict(cert)
            results.append(row)
            key = {
                CertificateStatus.EXPIRED: "expired",
                CertificateStatus.EXPIRING_SOON: "warning",
                CertificateStatus.ACTIVE: "normal",
            }.get(cert.status)
            if key:
                self.cert_stats[key] += 1
            detail = {
                "name": Path(path).name,
                "expiry_date": row["valid_to"],
                "subject": cert.subject,
                "status": row["status"],
            }
            if key == "expired":
                self.expired_certs.append(detail)
            elif key == "warning":
                self.warning_certs.append(detail)
        return results

    def export_to_excel(self, certs, save_path=None, report_title="Отчет"):
        from certificate_analyzer.infrastructure.reports.excel_exporter import (
            ExcelReportExporter,
        )

        return ExcelReportExporter(self.export_folder).export_rows(
            certs, save_path, report_title
        )

    def export_to_pdf(
        self,
        certs,
        save_path=None,
        figure=None,
        report_title="Отчет",
        include_chart=True,
    ):
        from certificate_analyzer.infrastructure.reports.pdf_exporter import (
            PdfReportExporter,
        )

        return PdfReportExporter(self.export_folder).export_rows(
            certs, save_path, report_title, figure if include_chart else None
        )
