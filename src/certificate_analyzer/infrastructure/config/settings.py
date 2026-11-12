"""Валидируемые настройки приложения с поддержкой переменных окружения."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field, StrictInt, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from certificate_analyzer.constants import CHECK_INTERVAL, WARNING_DAYS


class Settings(BaseSettings):
    """Схема конфигурации приложения Certificate Analyzer."""

    model_config = SettingsConfigDict(
        env_prefix="CERTIFICATE_ANALYZER_",
        extra="ignore",
        validate_assignment=True,
        hide_input_in_errors=True,
    )
    folders: dict[str, str] = Field(default_factory=lambda: {
        "Сотрудники": str(Path.home() / "Certs"),
        "Руководство": str(Path.home() / "ImportantCerts"),
    })
    mchd_folder: str = Field(default_factory=lambda: str(Path.home() / "MCHD"), min_length=1)
    export_folder: str = Field(default_factory=lambda: str(Path.home() / "CertificateReports"), min_length=1)
    phonebook_path: str | None = None
    database_path: str | None = None
    storage_folder: str | None = None
    warning_days: StrictInt = Field(default=WARNING_DAYS, ge=0)
    check_interval: StrictInt = Field(default=CHECK_INTERVAL, gt=0)
    notification_urls: list[str] = Field(default_factory=list, repr=False)
    rocketchat_webhook_url: str = Field(default="", repr=False)

    @field_validator("rocketchat_webhook_url")
    @classmethod
    def valid_rocketchat_webhook(cls, value: str) -> str:
        """Проверяет валидность URL входящего вебхука Rocket.Chat."""
        from certificate_analyzer.infrastructure.notifications.rocketchat import rocketchat_apprise_url
        value = value.strip()
        if value:
            rocketchat_apprise_url(value)
        return value

    @field_validator("database_path", "storage_folder")
    @classmethod
    def nonempty_optional_path(cls, value: str | None) -> str | None:
        """Запрещает пустые строковые пути для необязательных параметров."""
        if value is not None and not value.strip():
            raise ValueError("Путь должен быть непустым")
        return value

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        file_secret_settings: Any,
    ) -> tuple[Any, ...]:
        """Кастомизирует источники загрузки настроек, преобразуя числа из окружения."""
        def environment() -> dict[str, Any]:
            values = env_settings()
            for key in ("warning_days", "check_interval"):
                value = values.get(key)
                if isinstance(value, str) and value.strip().lstrip("+-").isdigit():
                    values[key] = int(value)
            return values
        return init_settings, environment

    @field_validator("notification_urls")
    @classmethod
    def valid_notification_urls(cls, values: list[str]) -> list[str]:
        """Проверяет корректность URL каналов Apprise."""
        from apprise import Apprise
        for value in values:
            if not value.strip() or not Apprise().add(value):
                raise ValueError("Некорректный адрес канала Apprise")
        return values

    def updated(self, **changes: Any) -> Settings:
        """Возвращает валидированную копию с изменениями."""
        return type(self)(**{**self.model_dump(), **changes})
