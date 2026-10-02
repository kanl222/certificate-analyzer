"""Базовый абстрактный класс для отправки уведомлений."""

from typing import Protocol


class NotificationBackend(Protocol):
    """Абстрактный интерфейс бэкенда уведомлений."""

    def send(self, title: str, message: str, notification_type: str = "info", **metadata) -> None:
        """Отправляет уведомление.

        Args:
            title: Заголовок уведомления.
            message: Текст сообщения.
        """
        ...
