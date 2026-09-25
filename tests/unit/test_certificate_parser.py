import pytest
from cryptography.hazmat.primitives.serialization import Encoding

from certificate_analyzer.infrastructure.certificates.x509_parser import X509Parser


@pytest.mark.parametrize("encoding", [Encoding.PEM, Encoding.DER])
def test_parses_metadata(certificate_file, encoding):
    path = certificate_file(encoding=encoding)
    cert = X509Parser.parse(path)
    assert cert.subject == "Иванов Иван"
    assert cert.employee is not None
    assert cert.employee.office == "101"
    assert cert.employee.department == "Отдел кадров"
    assert cert.valid_to.tzinfo is not None
    assert len(cert.fingerprint_sha256) == 64
    assert cert.email == "ivan@example.test"
    assert cert.source_path == str(path.resolve())


def test_mixed_folder_keeps_errors_and_persists_records(
    tmp_path, certificate_file, application
):
    certificate_file(days=-1)
    (tmp_path / "broken.CER").write_text("broken")
    service = application.certificates
    result = service.import_folder(tmp_path)
    assert len(result.certificates) == 1
    assert len(result.errors) == 1
    assert service.statistics()["EXPIRED"] == 1
    empty = tmp_path / "empty"
    empty.mkdir()
    assert service.import_folder(empty).certificates == []
    assert service.statistics()["total"] == 1
