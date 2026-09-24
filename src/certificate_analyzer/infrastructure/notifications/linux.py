"""Уведомления для ОС Linux."""

import logging
import subprocess

from certificate_analyzer.infrastructure.notifications.base import NotificationBackend

logger = logging.getLogger(__name__)


class LinuxDesktopNotifier(NotificationBackend):
    """Реализация отправки уведомлений в Linux (через notify-send)."""

    def send(self, title: str, message: str) -> None:
        """Отправляет всплывающее уведомление с помощью системной утилиты notify-send.

        Args:
            title: Заголовок уведомления.
            message: Текст сообщения.
        """
        try:
            subprocess.run(["notify-send", title, message], check=False)
        except FileNotFoundError:
            logger.warning(
                "Утилита notify-send не найдена. Сообщение: [%s] %s", title, message
            )
        except Exception as e:
            logger.error("Ошибка отправки notify-send: %s", e)
