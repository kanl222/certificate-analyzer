"""Форматирование и сборка текстов уведомлений приложения."""

from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class NotificationMessage:
    """Сформированное сообщение для отправки."""

    title: str
    message: str
    notification_type: str
    metadata: dict[str, Any]


class NotificationMessageBuilder:
    """Генератор стандартизированных заголовков и текстов уведомлений."""

    @staticmethod
    def get_hostname() -> str:
        """Возвращает сетевое имя текущего компьютера."""
        try:
            return socket.gethostname()
        except Exception:
            return "unknown-host"

    @classmethod
    def expired_certificates(
        cls,
        count: int,
        total: int,
        host_info: str | None = None,
    ) -> NotificationMessage:
        """Формирует уведомление об истёкших сертификатах."""
        host: str = host_info or cls.get_hostname()
        return NotificationMessage(
            title=f"Срок действия сертификатов истёк [Компьютер: {host}]",
            message=f"Просрочено: {count}. Всего сертификатов: {total}. Хранилище: {host}.",
            notification_type="error",
            metadata={
                "category": "expired",
                "count": count,
                "total": total,
                "host": host,
            },
        )

    @classmethod
    def expiring_certificates(
        cls,
        count: int,
        total: int,
        host_info: str | None = None,
    ) -> NotificationMessage:
        """Формирует уведомление о сертификатах с истекающим сроком действия."""
        host: str = host_info or cls.get_hostname()
        return NotificationMessage(
            title=f"Срок действия сертификатов скоро истечёт [Компьютер: {host}]",
            message=f"Истекает: {count}. Всего сертификатов: {total}. Хранилище: {host}.",
            notification_type="warning",
            metadata={
                "category": "expiring",
                "count": count,
                "total": total,
                "host": host,
            },
        )

    @classmethod
    def test_connection(
        cls,
        channel_name: str = "Rocket.Chat",
        host_info: str | None = None,
    ) -> NotificationMessage:
        """Формирует тестовое сообщение для проверки каналов связи."""
        host: str = host_info or cls.get_hostname()
        return NotificationMessage(
            title="Тестовое уведомление",
            message=f"Подключение Certificate Analyzer с компьютера «{host}» к {channel_name} успешно настроено!",
            notification_type="success",
            metadata={
                "category": "test",
                "channel": channel_name,
                "host": host,
            },
        )
