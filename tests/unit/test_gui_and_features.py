"""Тесты для новых интерфейсных и сервисных возможностей."""

from unittest.mock import Mock

from certificate_analyzer.infrastructure.notifications.message_builder import (
    NotificationMessageBuilder,
)


def test_notification_message_builder_formatting():
    """Проверяет стандартизацию текстов и заголовков уведомлений."""
    msg_expired = NotificationMessageBuilder.expired_certificates(count=3, total=10, host_info="SERVER-TEST")
    assert "SERVER-TEST" in msg_expired.title
    assert "Просрочено: 3" in msg_expired.message
    assert "SERVER-TEST" in msg_expired.message
    assert msg_expired.notification_type == "error"

    msg_expiring = NotificationMessageBuilder.expiring_certificates(count=2, total=10, host_info="SERVER-TEST")
    assert "SERVER-TEST" in msg_expiring.title
    assert "Истекает: 2" in msg_expiring.message
    assert msg_expiring.notification_type == "warning"

    msg_test = NotificationMessageBuilder.test_connection("Rocket.Chat", host_info="NODE-1")
    assert "Тестовое уведомление" in msg_test.title
    assert "NODE-1" in msg_test.message
    assert "Rocket.Chat" in msg_test.message
    assert msg_test.notification_type == "success"


def test_ipc_client_ping(tmp_path):
    """Проверяет метод ping в клиенте WriteClient."""
    from certificate_analyzer.runtime.ipc import WriteClient

    client = WriteClient(tmp_path / "test.db")
    client.call = Mock(return_value=({"pid": 1234, "database": "test.db"}, {}))

    result = client.ping()
    assert result["pid"] == 1234
    client.call.assert_called_once_with(method="ping")
