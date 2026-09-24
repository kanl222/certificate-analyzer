from datetime import UTC, datetime

from certificate_analyzer.application.dto.certificate_dto import CertificateDTO
from certificate_analyzer.domain.enums.certificate_status import CertificateStatus

EMPTY = "—"


class CertificateMapper:

    @staticmethod
    def to_dto(cert) -> CertificateDTO:
        status, color = CertificateMapper._status_view(cert)

        employee = cert.employee

        return CertificateDTO(
            file_name=str(cert.source_path or EMPTY),
            file_type="Сертификат",

            valid_from=cert.valid_from.strftime("%d.%m.%Y"),
            valid_to=cert.valid_to.strftime("%d.%m.%Y"),

            subject_cn=cert.subject or EMPTY,
            serial_number=cert.serial_number or EMPTY,

            email=cert.email or EMPTY,

            office_number=(
                employee.office
                if employee and employee.office
                else EMPTY
            ),

            department=(
                employee.department
                if employee and employee.department
                else EMPTY
            ),

            phone=(
                ", ".join(employee.phones)
                if employee and employee.phones
                else EMPTY
            ),

            status=status,
            color=color,
        )

    @staticmethod
    def _status_view(cert) -> tuple[str, str]:
        if cert.status is CertificateStatus.EXPIRING_SOON:
            days = max(
                0,
                (
                    cert.valid_to.date()
                    - datetime.now(UTC).date()
                ).days,
            )

            return f"Истекает ({days} дн.)", "#ffd54f"

        return {
            CertificateStatus.EXPIRED:
                ("Просрочен", "#e57373"),

            CertificateStatus.ACTIVE:
                ("Активен", "#81c784"),

            CertificateStatus.INVALID:
                ("Недействителен", "#e57373"),

            CertificateStatus.REVOKED:
                ("Отозван", "#e57373"),
        }.get(
            cert.status,
            ("Неизвестен", "#bdbdbd"),
        )