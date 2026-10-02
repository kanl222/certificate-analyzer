from datetime import timezone, datetime, timedelta
UTC = timezone.utc

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


@pytest.fixture(autouse=True)
def isolated_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("CERTIFICATE_ANALYZER_HOME", str(tmp_path / "profile"))
    yield
    # CLI starts a persistent user daemon; don't leak test daemons between tests.
    from certificate_analyzer.runtime.ipc import WriteClient, WriterUnavailable, WriteCommandError, token_path
    path = tmp_path / "profile" / "certificates.db"
    if token_path(path).exists():
        try:
            WriteClient(path, timeout=3).call(method="stop")
        except (WriterUnavailable, WriteCommandError):
            pass


@pytest.fixture
def application(tmp_path):
    from certificate_analyzer.bootstrap import create_application
    from certificate_analyzer.infrastructure.config.settings import Settings

    with create_application(
        settings=Settings(
            folders={},
            database_path=str(tmp_path / "db" / "test.sqlite"),
            storage_folder=str(tmp_path / "storage"),
            export_folder=str(tmp_path / "reports"),
        )
    ) as app:
        yield app


@pytest.fixture
def certificate_file(tmp_path):
    def create(name="cert.pem", days=90, encoding=serialization.Encoding.PEM):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, "Иванов Иван"),
                x509.NameAttribute(NameOID.EMAIL_ADDRESS, "ivan@example.test"),
                x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "101"),
                x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Отдел кадров"),
            ]
        )
        now = datetime.now(UTC)
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(key.public_key())
            .serial_number(12345)
            .not_valid_before(now - timedelta(days=100))
            .not_valid_after(now + timedelta(days=days))
            .sign(key, hashes.SHA256())
        )
        path = tmp_path / name
        path.write_bytes(cert.public_bytes(encoding))
        return path

    return create


@pytest.fixture
def mchd_file(tmp_path):
    def create(
        name="mchd.xml",
        codes=("A", "B"),
        inn="123",
        namespace="urn:test",
        expiry="2030-01-01",
    ):
        path = tmp_path / name
        path.write_text(
            f'''<Доверенность xmlns="{namespace}" ИдФайл="old">
          <СвДов НомДовер="11111111-1111-1111-1111-111111111111" ВнНомДовер="internal" ДатаВыдДовер="2020-01-01" СрокДейст="{expiry}"/>
          <СвРосОрг КПП="456" НаимОрг="Организация &amp; Ко" ИННЮЛ="{inn}" ОГРН="789"/>
          <СвУпПред ТипПред="3"><СведФизЛ СНИЛС="111" ИННФЛ="222"/><ФИО Имя="Иван" Фамилия="Иванов"/></СвУпПред>
          <ЛицоБезДов><СвФЛ ИННФЛ="999"/><ФИО Фамилия="Директор" Имя="Пётр"/></ЛицоБезДов>
          <СвПолн>{"".join(f'<МашПолн КодПолн="{c}" НаимПолн="Полномочие {c}"/>' for c in codes)}</СвПолн>
          <ДругойИдентификатор>11111111-1111-1111-1111-111111111111</ДругойИдентификатор>
        </Доверенность>''',
            encoding="utf-8",
        )
        return path

    return create
