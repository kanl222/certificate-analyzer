"""Модуль для парсинга сертификатов X.509."""

import re
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509.oid import NameOID

from certificate_analyzer.domain.models.certificate import Certificate


class X509Parser:
    """Парсер цифровых сертификатов X.509.

    Поддерживает сертификаты в форматах DER и PEM.

    Парсер отвечает только за чтение и преобразование X.509
    в доменную модель Certificate.

    Вычисление статуса сертификата выполняется отдельно
    на уровне доменной логики.
    """

    @classmethod
    def parse(
        cls,
        cert_source: bytes | str | Path,
    ) -> Certificate:
        """Распарсить сертификат X.509.

        Args:
            cert_source:
                Байты сертификата либо путь к файлу сертификата.

        Returns:
            Доменная модель Certificate.

        Raises:
            TypeError:
                Если передан неподдерживаемый тип данных.

            ValueError:
                Если данные не являются корректным DER/PEM
                сертификатом X.509.

            OSError:
                Если файл сертификата невозможно прочитать.
        """

        cert_data = cls._read_source(cert_source)

        cert = cls._load_certificate(cert_data)

        model = cls._create_model(cert)
        if isinstance(cert_source, (str, Path)):
            model.source_path = str(Path(cert_source).resolve())
        return model

    @staticmethod
    def _read_source(
        cert_source: bytes | str | Path,
    ) -> bytes:
        """Получить байтовое представление сертификата."""

        if isinstance(cert_source, bytes):
            return cert_source

        if isinstance(cert_source, (str, Path)):
            path = Path(cert_source)

            return path.read_bytes()

        raise TypeError("cert_source должен иметь тип bytes, str или Path")

    @classmethod
    def parse_for_import(cls, source):
        """Parse once; return metadata and a public certificate in canonical DER."""
        cert = cls._load_certificate(cls._read_source(source))
        return cls._create_model(cert), cert.public_bytes(serialization.Encoding.DER)

    @staticmethod
    def _load_certificate(
        cert_data: bytes,
    ) -> x509.Certificate:
        """Загрузить DER или PEM сертификат."""

        if not cert_data:
            raise ValueError("Сертификат не содержит данных")

        if b"-----BEGIN CERTIFICATE-----" in cert_data:
            try:
                return x509.load_pem_x509_certificate(cert_data)
            except ValueError as exc:
                raise ValueError("Не удалось распарсить PEM сертификат") from exc

        try:
            return x509.load_der_x509_certificate(cert_data)
        except ValueError as exc:
            raise ValueError("Не удалось распарсить DER сертификат") from exc

    @staticmethod
    def _create_model(
        cert: x509.Certificate,
    ) -> Certificate:
        """Преобразовать X.509 Certificate в доменную модель."""

        fingerprint = cert.fingerprint(hashes.SHA256()).hex().upper()

        subject = X509Parser._get_common_name(cert.subject)

        issuer = X509Parser._get_common_name(cert.issuer)

        serial_number = format(
            cert.serial_number,
            "X",
        )

        email = ", ".join(
            str(a.value)
            for a in cert.subject.get_attributes_for_oid(NameOID.EMAIL_ADDRESS)
        )
        office = ", ".join(
            str(a.value)
            for a in cert.subject.get_attributes_for_oid(
                NameOID.ORGANIZATIONAL_UNIT_NAME
            )
            if re.search(r"\d", str(a.value))
        )
        department = ", ".join(
            str(a.value)
            for a in cert.subject.get_attributes_for_oid(
                NameOID.ORGANIZATIONAL_UNIT_NAME
            )
            if not re.search(r"\d", str(a.value))
        )

        from certificate_analyzer.domain.models.employee import Employee

        employee = Employee(
            full_name=subject,
            department=department if department else None,
            office=office if office else None,
        )

        return Certificate(
            fingerprint_sha256=fingerprint,
            subject=subject,
            issuer=issuer,
            valid_from=cert.not_valid_before_utc,
            valid_to=cert.not_valid_after_utc,
            serial_number=serial_number,
            has_private_key_link=False,
            owner_name=subject,
            employee=employee,
            email=email,
        )

    @staticmethod
    def _get_common_name(
        name: x509.Name,
    ) -> str:
        """Получить CN либо полное X.509 имя."""

        attributes = name.get_attributes_for_oid(NameOID.COMMON_NAME)

        if attributes:
            return str(attributes[0].value)

        return name.rfc4514_string()
