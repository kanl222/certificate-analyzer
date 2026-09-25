"""Перечисление статусов жизненного цикла заявки на сертификат."""

from enum import Enum


class CertificateRequestStatus(str, Enum):
    """Статусы процесса выпуска и получения цифрового сертификата."""

    NOT_SUBMITTED = "NOT_SUBMITTED"
    SUBMITTED = "SUBMITTED"
    IN_PROGRESS = "IN_PROGRESS"
    ISSUED = "ISSUED"
    RECEIVED = "RECEIVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

    @property
    def label(self) -> str:
        """Понятное пользователю наименование статуса на русском языке.

        Returns:
            str: Локализованное название статуса.
        """
        labels = {
            CertificateRequestStatus.NOT_SUBMITTED: "Не подана",
            CertificateRequestStatus.SUBMITTED: "Подана",
            CertificateRequestStatus.IN_PROGRESS: "В работе",
            CertificateRequestStatus.ISSUED: "Выпущен",
            CertificateRequestStatus.RECEIVED: "Получен",
            CertificateRequestStatus.REJECTED: "Отклонена",
            CertificateRequestStatus.CANCELLED: "Аннулирована",
        }
        return labels.get(self, self.value)
