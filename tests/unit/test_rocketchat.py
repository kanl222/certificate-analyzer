import json
from unittest.mock import Mock

import pytest

from certificate_analyzer.infrastructure.config.settings import Settings
from certificate_analyzer.infrastructure.notifications.apprise_backend import AppriseNotificationBackend
from certificate_analyzer.infrastructure.notifications.rocketchat import rocketchat_apprise_url


@pytest.mark.parametrize("webhook", [
    "https://chat.example.org/hooks/integration123/token456",
    "http://chat.example.org:3000/hooks/integration123/token456",
])
def test_apprise_posts_to_incoming_webhook_without_login(monkeypatch, webhook):
    from apprise.plugins import rocketchat
    response = Mock(status_code=200, content=b'{"success":true}')
    post = Mock(return_value=response)
    monkeypatch.setattr(rocketchat.requests, "post", post)
    backend = AppriseNotificationBackend([rocketchat_apprise_url(webhook)])
    backend.send("Истекают сертификаты", "Истекает: 2", notification_type="warning")
    post.assert_called_once()
    assert post.call_args.args[0] == webhook
    payload = json.loads(post.call_args.kwargs["data"])
    assert "Истекает: 2" in payload["text"]
    assert "Истекают сертификаты" in payload["text"]
    assert "channel" not in payload
    assert post.call_args.kwargs["verify"] is True


@pytest.mark.parametrize("webhook", [
    "https://chat.example.org", "https://chat.example.org/hooks/id",
    "https://chat.example.org/hooks/id/", "ftp://chat.example.org/hooks/id/token",
    "https://user:pass@chat.example.org/hooks/id/token",
    "https://chat.example.org/hooks/id/token?token=hidden",
    "https://chat.example.org/hooks/id/token#channel",
    "https://chat.example.org:bad/hooks/id/token",
])
def test_invalid_webhook_is_rejected_without_exposing_token(webhook):
    with pytest.raises(ValueError) as caught:
        Settings(rocketchat_webhook_url=webhook)
    assert webhook not in str(caught.value)


def test_rocketchat_configuration_roundtrip_and_assembly(tmp_path, monkeypatch):
    from certificate_analyzer.application.services import notification_service
    from certificate_analyzer.infrastructure.config.config_loader import load_settings, save_settings
    monkeypatch.setattr(notification_service, "default_desktop_backend", Mock())
    webhook = "https://chat.example.org/hooks/integration123/token456"
    path = tmp_path / "settings.json"
    save_settings(Settings(rocketchat_webhook_url=webhook), path)
    settings = load_settings(path)
    assert settings.rocketchat_webhook_url == webhook
    assert webhook not in repr(settings)
    backends = notification_service.notification_backend(rocketchat_webhook_url=settings.rocketchat_webhook_url).backends
    assert any(isinstance(backend, AppriseNotificationBackend) for backend in backends)
    assert not any(isinstance(backend, AppriseNotificationBackend) for backend in notification_service.notification_backend().backends)
