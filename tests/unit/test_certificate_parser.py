import pytest
from cryptography.hazmat.primitives.serialization import Encoding

from certificate_analyzer.application.services.certificate_service import (
    CertificateAnalyzerCore,
)
from certificate_analyzer.infrastructure.certificates.x509_parser import X509Parser
from certificate_analyzer.infrastructure.config.settings import Settings


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


def test_mixed_folder_keeps_errors_and_clears_state(tmp_path, certificate_file):
    certificate_file(days=-1)
    (tmp_path / "broken.CER").write_text("broken")
    core = CertificateAnalyzerCore(Settings(export_folder=str(tmp_path / "reports")))
    core.scan_certificates(tmp_path)
    assert len(core.parse_certificates()) == 1
    assert len(core.errors) == 1
    assert core.cert_stats["expired"] == 1
    empty = tmp_path / "empty"
    empty.mkdir()
    core.scan_certificates(empty)
    assert core.parse_certificates() == []
    assert not core.errors and not core.expired_certs
