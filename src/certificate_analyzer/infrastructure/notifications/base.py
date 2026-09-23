"""Базовый абстрактный класс для отправки уведомлений."""

from typing import Protocol


class NotificationBackend(Protocol):
    """Абстрактный интерфейс бэкенда уведомлений."""

    def send(self, title: str, message: str) -> None:
        """Отправляет уведомление.

        Args:
            title: Заголовок уведомления.
            message: Текст сообщения.
        """
        ...
