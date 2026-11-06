"""Adapter for configured Apprise channels; no network activity during setup."""

from apprise import Apprise, NotifyFormat, NotifyType

from certificate_analyzer.infrastructure.notifications.base import NotificationBackend


class AppriseNotificationBackend(NotificationBackend):
    def __init__(self, urls):
        self.client = Apprise()
        for url in urls:
            if not self.client.add(url):
                raise ValueError("Некорректный адрес канала Apprise")

    def send(self, title, message, notification_type="info", **kwargs):
        kinds = {
            "info": NotifyType.INFO, "success": NotifyType.SUCCESS,
            "warning": NotifyType.WARNING, "error": NotifyType.FAILURE,
        }
        if not self.client.notify(
            title=title, body=message, notify_type=kinds.get(notification_type, NotifyType.INFO),
            body_format=NotifyFormat.TEXT,
        ):
            raise RuntimeError("Не удалось доставить уведомление через один или несколько каналов Apprise")
