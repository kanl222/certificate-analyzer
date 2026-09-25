"""Доменная модель файла цифрового сертификата."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class CertificateFile:
    """Сущность физического файла сертификата в файловой системе или хранилище.

    Attributes:
        path: Полный путь к файлу сертификата.
        fingerprint: SHA-256 отпечаток сертификата, к которому привязан файл.
        file_name: Имя файла с расширением.
        size: Размер файла в байтах.
        first_seen_at: Дата и время первого обнаружения файла.
        last_seen_at: Дата и время последней проверки/модификации файла.
        content_sha256: Хеш SHA-256 содержимого исходного файла.
    """

    path: str
    fingerprint: str
    file_name: str
    size: int
    first_seen_at: datetime
    last_seen_at: datetime
    content_sha256: str = ""
