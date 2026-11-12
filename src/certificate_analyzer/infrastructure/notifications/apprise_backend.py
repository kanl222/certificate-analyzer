"""Адаптер для настроенных каналов Apprise; без сетевой активности при инициализации."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from apprise import Apprise, NotifyFormat, NotifyType

from certificate_analyzer.infrastructure.notifications.base import NotificationBackend


class AppriseNotificationBackend(NotificationBackend):
    """Бэкенд отправки уведомлений через библиотеку Apprise."""

    def __init__(self, urls: Iterable[str]) -> None:
        """Инициализирует клиент Apprise списком URL каналов.

        Args:
            urls: Итерируемый объект со строками адресов каналов.

        Raises:
            ValueError: Если передан некорректный адрес канала.
        """
        self.client: Apprise = Apprise()
        for url in urls:
            if not self.client.add(url):
                raise ValueError("Некорректный адрес канала Apprise")

    def send(self, title: str, message: str, notification_type: str = "info", **kwargs: Any) -> None:
        """Отправляет уведомление во все зарегистрированные каналы.

        Args:
            title: Заголовок уведомления.
            message: Текст уведомления.
            notification_type: Тип уведомления ('info', 'success', 'warning', 'error').
            **kwargs: Дополнительные параметры.

        Raises:
            RuntimeError: При неудачной отправке уведомления.
        """
        kinds: dict[str, NotifyType] = {
            "info": NotifyType.INFO,
            "success": NotifyType.SUCCESS,
            "warning": NotifyType.WARNING,
            "error": NotifyType.FAILURE,
        }
        if not self.client.notify(
            title=title,
            body=message,
            notify_type=kinds.get(notification_type, NotifyType.INFO),
            body_format=NotifyFormat.TEXT,
        ):
            raise RuntimeError("Не удалось доставить уведомление через один или несколько каналов Apprise")
