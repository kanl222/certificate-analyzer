import pytest
from io import BytesIO
from unittest.mock import patch
from cryptography.hazmat.primitives.serialization import Encoding

from certificate_analyzer.infrastructure.certificates.x509_parser import X509Parser


@pytest.mark.parametrize("method", [X509Parser.parse, X509Parser.parse_for_import])
@pytest.mark.parametrize("as_file", [False, True])
def test_rejects_oversized_certificate_before_decoding(tmp_path, method, as_file):
    data = b"x" * (X509Parser.MAX_CERTIFICATE_SIZE + 1)
    source = data
    if as_file:
        source = tmp_path / "oversized.cer"
        source.write_bytes(data)
    with patch.object(X509Parser, "_load_certificate") as load:
        with pytest.raises(ValueError, match="Размер сертификата"):
            method(source)
        load.assert_not_called()


def test_file_read_is_bounded(tmp_path):
    stream = BytesIO(b"x" * (X509Parser.MAX_CERTIFICATE_SIZE + 10))
    with patch("pathlib.Path.open", return_value=stream), patch.object(
        stream, "read", wraps=stream.read
    ) as read:
        with pytest.raises(ValueError, match="Размер сертификата"):
            X509Parser.parse(tmp_path / "large.cer")
        read.assert_called_once_with(X509Parser.MAX_CERTIFICATE_SIZE + 1)


def test_exact_size_limit_is_accepted():
    data = b"x" * X509Parser.MAX_CERTIFICATE_SIZE
    assert X509Parser._read_source(data) == data


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
