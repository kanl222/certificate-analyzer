from unittest.mock import Mock

import pytest
from apprise import NotifyFormat, NotifyType

from certificate_analyzer.infrastructure.notifications.apprise_backend import AppriseNotificationBackend


@pytest.mark.parametrize("kind,expected", [("info", NotifyType.INFO), ("warning", NotifyType.WARNING), ("error", NotifyType.FAILURE), ("success", NotifyType.SUCCESS)])
def test_apprise_routes_type_and_ignores_internal_metadata(monkeypatch, kind, expected):
    backend = AppriseNotificationBackend(["json://localhost:9999"])
    notify = Mock(return_value=True)
    monkeypatch.setattr(backend.client, "notify", notify)
    backend.send("Заголовок", "Сообщение", notification_type=kind, duration=10, expired_count=2)
    notify.assert_called_once_with(title="Заголовок", body="Сообщение", notify_type=expected, body_format=NotifyFormat.TEXT)


def test_delivery_failure_does_not_stop_other_channels(monkeypatch):
    from certificate_analyzer.infrastructure.notifications.composite import CompositeNotificationBackend
    backend = AppriseNotificationBackend(["json://localhost:9999"])
    monkeypatch.setattr(backend.client, "notify", lambda **kwargs: False)
    other = Mock()
    CompositeNotificationBackend([backend, other]).send("Title", "Body")
    other.send.assert_called_once()
    with pytest.raises(RuntimeError):
        backend.send("Title", "Body")


def test_configured_apprise_channels_are_connected_without_network(monkeypatch):
    from certificate_analyzer.application.services import notification_service
    desktop = Mock()
    monkeypatch.setattr(notification_service, "default_desktop_backend", lambda: desktop)
    assert not any(isinstance(backend, AppriseNotificationBackend) for backend in notification_service.notification_backend().backends)
    composite = notification_service.notification_backend(["json://localhost:9999"])
    backend = next(backend for backend in composite.backends if isinstance(backend, AppriseNotificationBackend))
    notify = Mock(return_value=True)
    monkeypatch.setattr(backend.client, "notify", notify)
    composite.send("Title", "Body", notification_type="warning")
    desktop.send.assert_called_once()
    notify.assert_called_once()
