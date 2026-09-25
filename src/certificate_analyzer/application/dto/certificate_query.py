from dataclasses import dataclass
from datetime import date
from certificate_analyzer.domain.enums.certificate_status import CertificateStatus


@dataclass(frozen=True)
class CertificateQuery:
    search: str = ""
    status: CertificateStatus | None = None
    date_from: date | None = None
    date_to: date | None = None
    sort: str = "subject"
    descending: bool = False
    limit: int | None = 100
    offset: int = 0

    def __post_init__(self):
        if self.limit is not None and self.limit <= 0:
            raise ValueError("limit должен быть положительным")
        if self.offset < 0:
            raise ValueError("offset должен быть неотрицательным")
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("Начало периода позже окончания")
