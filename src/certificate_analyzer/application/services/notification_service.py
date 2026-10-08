import logging
import sys
import threading
import time
from datetime import datetime

from certificate_analyzer.domain.enums.notification_type import NotificationType
from certificate_analyzer.infrastructure.notifications.api_notifier import (
    ApiNotificationBackend,
)
from certificate_analyzer.infrastructure.notifications.composite import (
    CompositeNotificationBackend,
)


def default_desktop_backend():
    """Возвращает платформозависимый бэкенд рабочего стола."""
    if sys.platform == "win32":
        from certificate_analyzer.infrastructure.notifications.windows import (
            WindowsToastNotifier,
        )

        return WindowsToastNotifier()
    if sys.platform.startswith("linux"):
        from certificate_analyzer.infrastructure.notifications.linux import (
            LinuxDesktopNotifier,
        )

        return LinuxDesktopNotifier()
    from certificate_analyzer.infrastructure.notifications.fallback import (
        LoggingNotificationBackend,
    )

    return LoggingNotificationBackend()


def notification_backend():
    """Создает составной бэкенд по умолчанию (десктопные уведомления + API заглушка)."""
    desktop = default_desktop_backend()
    api_stub = ApiNotificationBackend(stub_mode=True)
    return CompositeNotificationBackend([desktop, api_stub])


class PushNotificationManager:
    """Менеджер push-уведомлений с поддержкой многоканальной рассылки (Desktop, API stub) и истории."""

    def __init__(self, backend=None, history_store=None):
        if backend is not None:
            self.backend = backend
        else:
            self.backend = notification_backend()

        self.history_store = history_store
        self.notification_interval = 3600
        self.last_notification_time: dict[str, float] = {}
        self._last_messages: dict[tuple, float] = {}
        self._stop = threading.Event()
        self.thread: threading.Thread | None = None
        self.running: bool = False

    @property
    def api_backend(self) -> ApiNotificationBackend | None:
        """Возвращает подключенный ApiNotificationBackend при его наличии в Composite backend."""
        if isinstance(self.backend, ApiNotificationBackend):
            return self.backend
        if isinstance(self.backend, CompositeNotificationBackend):
            for b in self.backend.backends:
                if isinstance(b, ApiNotificationBackend):
                    return b
        return None

    def configure_api(
        self,
        api_url: str = "https://api.example.com/v1/notifications",
        api_key: str | None = None,
        stub_mode: bool = True,
    ) -> ApiNotificationBackend:
        """Настраивает бэкенд отправки через API или добавляет его, если он ещё не подключен."""
        existing = self.api_backend
        if existing:
            existing.api_url = api_url
            existing.api_key = api_key
            existing.stub_mode = stub_mode
            return existing

        new_api = ApiNotificationBackend(
            api_url=api_url,
            api_key=api_key,
            stub_mode=stub_mode,
        )
        if isinstance(self.backend, CompositeNotificationBackend):
            self.backend.add_backend(new_api)
        else:
            self.backend = CompositeNotificationBackend([self.backend, new_api])
        return new_api

    def set_interval(self, hours: int) -> None:
        """Устанавливает периодичность проверок в часах."""
        if hours <= 0:
            raise ValueError("Интервал должен быть больше нуля")
        self.notification_interval = hours * 3600

    def send_notification(
        self,
        title: str,
        message: str,
        duration: int = 10,
        notification_type: str = "info",
        **kwargs,
    ) -> bool:
        """Отправляет уведомление во все активные бэкенды и сохраняет в историю."""
        now = time.monotonic()
        key = (title, message)
        if now - self._last_messages.get(key, float("-inf")) < 300:
            return False

        # Отправка во все зарегистрированные бэкенды
        self.backend.send(
            title=title,
            message=message,
            notification_type=notification_type,
            duration=duration,
            **kwargs,
        )

        self._last_messages = {
            k: t for k, t in self._last_messages.items() if now - t < 3600
        }
        self._last_messages[key] = now

        # Сохранение в историю уведомлений, если подключен history_store
        if self.history_store is not None:
            try:
                history_item = {
                    "time": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                    "title": title,
                    "message": message,
                    "type": notification_type,
                }
                history = self.history_store.load()
                history.insert(0, history_item)
                self.history_store.save(history)
            except Exception as e:
                logging.getLogger(__name__).warning("Не удалось сохранить уведомление в историю: %s", e)

        return True

    def check_and_notify_expired(self, expired_count: int, warning_count: int, total_count: int) -> bool:
        """Send expired/expiring messages independently with separate rate limits."""
        now = time.monotonic()
        sent_any = False
        for category, count, title, label, kind in (
            ("expired", expired_count, "Срок действия сертификатов истёк", "Просрочено", NotificationType.ERROR.value),
            ("expiring", warning_count, "Срок действия сертификатов скоро истечёт", "Истекает", NotificationType.WARNING.value),
        ):
            if count <= 0 or now - self.last_notification_time.get(category, float("-inf")) < self.notification_interval:
                continue
            try:
                sent = self.send_notification(
                    title=title, message=f"{label}: {count}. Всего сертификатов: {total_count}.",
                    notification_type=kind, expired_count=expired_count,
                    warning_count=warning_count, total_count=total_count,
                )
            except Exception:
                logging.getLogger(__name__).exception("Не удалось отправить уведомление категории %s", category)
                continue
            if sent:
                self.last_notification_time[category] = now
                sent_any = True
        return sent_any

    def start_background_monitoring(self, callback, interval_seconds: int = 3600) -> None:
        """Запускает фоновый поток мониторинга с заданным интервалом в секундах."""
        if interval_seconds <= 0:
            raise ValueError("Интервал должен быть больше нуля")
        if self.thread and self.thread.is_alive():
            return
        self._stop.clear()
        self.running = True

        def loop():
            try:
                while not self._stop.is_set():
                    try:
                        callback()
                    except Exception:
                        logging.getLogger(__name__).exception("Ошибка мониторинга")
                    self._stop.wait(interval_seconds)
            finally:
                self.running = False

        self.thread = threading.Thread(target=loop, daemon=True)
        self.thread.start()

    def stop_monitoring(self) -> None:
        """Останавливает фоновый поток мониторинга."""
        self._stop.set()
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(timeout=2)
        self.running = False
