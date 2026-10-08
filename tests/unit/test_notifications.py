from unittest.mock import MagicMock
import pytest

from certificate_analyzer.application.services.notification_service import (
    PushNotificationManager,
)
from certificate_analyzer.domain.enums.notification_type import NotificationType
from certificate_analyzer.domain.models.notification import Notification
from certificate_analyzer.infrastructure.notifications.api_notifier import (
    ApiNotificationBackend,
)
from certificate_analyzer.infrastructure.notifications.composite import (
    CompositeNotificationBackend,
)


def test_expired_and_expiring_have_independent_notifications_and_intervals():
    backend = MagicMock()
    manager = PushNotificationManager(backend=backend)
    assert manager.check_and_notify_expired(2, 1, 10)
    assert backend.send.call_count == 2
    messages = [call.kwargs for call in backend.send.call_args_list]
    assert messages[0]["notification_type"] == "error"
    assert messages[1]["notification_type"] == "warning"
    assert "Истекает:" not in messages[0]["message"]
    assert "Просрочено:" not in messages[1]["message"]
    assert not manager.check_and_notify_expired(2, 1, 10)
    fresh = PushNotificationManager(backend=MagicMock())
    assert fresh.check_and_notify_expired(1, 0, 10)
    assert fresh.check_and_notify_expired(1, 2, 10)
    assert fresh.backend.send.call_count == 2


@pytest.mark.parametrize("backend_kind", ["windows", "linux", "logging"])
def test_desktop_backend_accepts_manager_metadata(backend_kind, monkeypatch, caplog):
    from certificate_analyzer.infrastructure.notifications.windows import WindowsToastNotifier
    from certificate_analyzer.infrastructure.notifications.linux import LinuxDesktopNotifier
    from certificate_analyzer.infrastructure.notifications.fallback import LoggingNotificationBackend
    import logging
    caplog.set_level(logging.INFO)
    delivered = MagicMock()
    if backend_kind == "windows":
        desktop = WindowsToastNotifier.__new__(WindowsToastNotifier)
        desktop._available = True
        desktop._toaster = MagicMock()
        desktop._toaster.show_toast = delivered
    elif backend_kind == "linux":
        desktop = LinuxDesktopNotifier()
        monkeypatch.setattr("certificate_analyzer.infrastructure.notifications.linux.subprocess.run", delivered)
    else:
        desktop = LoggingNotificationBackend()
    api = ApiNotificationBackend(stub_mode=True)
    manager = PushNotificationManager(backend=CompositeNotificationBackend([desktop, api]))
    assert manager.check_and_notify_expired(2, 1, 10)
    assert "unexpected keyword argument" not in caplog.text
    if backend_kind != "logging":
        assert delivered.call_count == 2
    else:
        assert "Просрочено: 2" in caplog.text
    assert api.history[0]["payload"]["metadata"]["expired_count"] == 2


def test_notification_domain_model():
    notif = Notification(
        title="Тест",
        message="Сообщение",
        notification_type=NotificationType.WARNING,
        metadata={"expired": 5},
    )
    d = notif.to_dict()
    assert d["title"] == "Тест"
    assert d["message"] == "Сообщение"
    assert d["notification_type"] == "warning"
    assert d["metadata"] == {"expired": 5}
    assert "timestamp" in d


def test_api_notification_backend_stub():
    backend = ApiNotificationBackend(
        api_url="https://api.corp.local/alerts",
        api_key="secret-key-123",
        stub_mode=True,
    )
    assert backend.stub_mode is True
    assert len(backend.history) == 0

    result = backend.send(
        title="Истекает сертификат",
        message="Сертификат Иванова истекает через 3 дня",
        notification_type="warning",
        cert_serial="ABC123XYZ",
    )

    assert result["status"] == "success"
    assert result["mode"] == "stub"
    assert result["url"] == "https://api.corp.local/alerts"
    assert len(backend.history) == 1

    payload = result["payload"]
    assert payload["title"] == "Истекает сертификат"
    assert payload["type"] == "warning"
    assert payload["source"] == "certificate-analyzer"
    assert payload["metadata"]["cert_serial"] == "ABC123XYZ"
    assert "notification_id" in payload

    backend.clear_history()
    assert len(backend.history) == 0


def test_composite_notification_backend():
    backend1 = MagicMock()
    backend2 = MagicMock()

    composite = CompositeNotificationBackend([backend1, backend2])
    composite.send("Заголовок", "Сообщение", notification_type="info")

    backend1.send.assert_called_once_with("Заголовок", "Сообщение", notification_type="info")
    backend2.send.assert_called_once_with("Заголовок", "Сообщение", notification_type="info")


def test_composite_notification_backend_error_isolation():
    failing_backend = MagicMock()
    failing_backend.send.side_effect = RuntimeError("Connection lost")
    working_backend = MagicMock()

    composite = CompositeNotificationBackend([failing_backend, working_backend])
    # Should not raise exception
    composite.send("Заголовок", "Сообщение")

    failing_backend.send.assert_called_once()
    working_backend.send.assert_called_once()


def test_push_notification_manager_with_api_stub():
    api_backend = ApiNotificationBackend(stub_mode=True)
    manager = PushNotificationManager(backend=api_backend)

    assert manager.api_backend is api_backend

    sent = manager.send_notification("Внимание", "Проверка связи", notification_type="info")
    assert sent is True
    assert len(api_backend.history) == 1
    assert api_backend.history[0]["payload"]["title"] == "Внимание"

    # Deduplication within 300s window
    duplicate_sent = manager.send_notification("Внимание", "Проверка связи")
    assert duplicate_sent is False
    assert len(api_backend.history) == 1


def test_push_notification_manager_check_and_notify_expired():
    api_backend = ApiNotificationBackend(stub_mode=True)
    manager = PushNotificationManager(backend=api_backend)

    # If no expired and no warning, should not send
    sent_empty = manager.check_and_notify_expired(0, 0, 10)
    assert sent_empty is False
    assert len(api_backend.history) == 0

    # With expired certificates
    sent_expired = manager.check_and_notify_expired(2, 1, 10)
    assert sent_expired is True
    assert len(api_backend.history) == 2

    last = api_backend.history[0]["payload"]
    assert last["type"] == "error"
    assert "Просрочено: 2" in last["message"]
    assert last["metadata"]["expired_count"] == 2
    assert last["metadata"]["warning_count"] == 1
    assert api_backend.history[1]["payload"]["type"] == "warning"


def test_push_notification_manager_configure_api():
    manager = PushNotificationManager(backend=MagicMock())
    api = manager.configure_api(api_url="https://webhook.site/test", api_key="token-abc", stub_mode=True)

    assert api.api_url == "https://webhook.site/test"
    assert api.api_key == "token-abc"
    assert api.stub_mode is True
    assert manager.api_backend is api
