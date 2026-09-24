from dataclasses import dataclass, field
from pathlib import Path
from certificate_analyzer.constants import CHECK_INTERVAL, WARNING_DAYS


@dataclass
class Settings:
    folders: dict[str, str] = field(
        default_factory=lambda: {
            "📁 Сотрудники": str(Path.home() / "Certs"),
            "📁 Руководство": str(Path.home() / "ImportantCerts"),
        }
    )
    mchd_folder: str = field(default_factory=lambda: str(Path.home() / "MCHD"))
    export_folder: str = field(
        default_factory=lambda: str(Path.home() / "CertificateReports")
    )
    phonebook_path: str | None = None
    warning_days: int = WARNING_DAYS
    check_interval: int = CHECK_INTERVAL

    def __post_init__(self):
        if not isinstance(self.folders, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in self.folders.items()
        ):
            raise ValueError("folders должен быть словарём путей")
        for name in ("mchd_folder", "export_folder"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"Некорректный путь: {name}")
        if type(self.warning_days) is not int or self.warning_days < 0:
            raise ValueError("warning_days должен быть неотрицательным целым числом")
        if type(self.check_interval) is not int or self.check_interval <= 0:
            raise ValueError("check_interval должен быть положительным целым числом")
