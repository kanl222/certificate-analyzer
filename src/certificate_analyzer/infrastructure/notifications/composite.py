"""Составной бэкенд для одновременной отправки уведомлений через несколько каналов."""

from __future__ import annotations

import logging
from typing import Any

from certificate_analyzer.infrastructure.notifications.base import NotificationBackend

logger = logging.getLogger(__name__)


class CompositeNotificationBackend(NotificationBackend):
    """Отправляет уведомление одновременно во все зарегистрированные бэкенды (Desktop, API и др.)."""

    def __init__(self, backends: list[NotificationBackend] | None = None) -> None:
        self.backends: list[NotificationBackend] = list(backends or [])

    def add_backend(self, backend: NotificationBackend) -> None:
        """Добавляет бэкенд в список рассылки."""
        if backend not in self.backends:
            self.backends.append(backend)

    def remove_backend(self, backend: NotificationBackend) -> None:
        """Удаляет бэкенд из списка рассылки."""
        if backend in self.backends:
            self.backends.remove(backend)

    def send(self, title: str, message: str, **kwargs: Any) -> None:
        """Рассылает уведомление во все бэкенды, изолируя сбои отдельных каналов."""
        for backend in self.backends:
            try:
                backend.send(title, message, **kwargs)
            except Exception as e:
                logger.error("Ошибка отправки через бэкенд %s: %s", type(backend).__name__, e)
