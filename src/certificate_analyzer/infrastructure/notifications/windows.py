"""Уведомления для ОС Windows."""

import logging
from certificate_analyzer.infrastructure.notifications.base import NotificationBackend

logger = logging.getLogger(__name__)


class WindowsToastNotifier(NotificationBackend):
    """Реализация отправки уведомлений в Windows."""

    def __init__(self) -> None:
        """Инициализирует Windows ToastNotifier."""
        try:
            from win10toast import ToastNotifier

            self._toaster = ToastNotifier()
            self._available = True
        except ImportError:
            logger.warning(
                "Библиотека win10toast не установлена. Уведомления Windows отключены."
            )
            self._toaster = None
            self._available = False

    def send(self, title: str, message: str) -> None:
        """Отправляет всплывающее уведомление Windows (Action Center).

        Args:
            title: Заголовок уведомления.
            message: Текст сообщения.
        """
        if not self._available or not self._toaster:
            logger.info(f"Windows Toast недоступен. Сообщение: [{title}] {message}")
            return

        try:
            self._toaster.show_toast(title, message, duration=10, threaded=True)
        except Exception as e:
            logger.error("Ошибка отправки Toast уведомления: %s", e)
