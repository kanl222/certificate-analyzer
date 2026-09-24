from dataclasses import dataclass
from certificate_analyzer.infrastructure.config.config_loader import load_settings
from certificate_analyzer.infrastructure.config.settings import Settings
from certificate_analyzer.application.services.certificate_service import (
    CertificateAnalyzerCore,
)


@dataclass
class ApplicationContainer:
    settings: Settings
    certificates: CertificateAnalyzerCore


def create_application(config_path=None):
    settings = load_settings(config_path)
    return ApplicationContainer(settings, CertificateAnalyzerCore(settings))
