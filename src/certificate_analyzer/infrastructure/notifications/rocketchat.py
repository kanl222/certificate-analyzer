"""Преобразование входящего вебхука Rocket.Chat в формат транспорта Apprise."""

from __future__ import annotations

from urllib.parse import urlencode, urlsplit


def rocketchat_apprise_url(webhook: str) -> str:
    """Преобразует стандартный URL входящего вебхука Rocket.Chat в URL формата Apprise.

    Принимает URL вида https://сервер/hooks/{integrationId}/{token} без отправки сетевых запросов.

    Args:
        webhook: Исходный URL вебхука.

    Returns:
        str: Сконфигурированный URL для Apprise.

    Raises:
        ValueError: Если передан некорректный формат адреса.
    """
    error = "Rocket.Chat: укажите URL вида https://сервер/hooks/id/token"
    try:
        parsed = urlsplit(webhook)
        port = parsed.port
        parts = parsed.path.split("/")
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment or any(char.isspace() for char in webhook)
                or len(parts) != 4 or parts[1] != "hooks" or not all(parts[2:])):
            raise ValueError(error)
    except ValueError:
        raise ValueError(error) from None
    scheme = "rockets" if parsed.scheme == "https" else "rocket"
    host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
    authority = f"{host}:{port}" if port is not None else host
    query = urlencode({"webhook": "/".join(parts[2:]), "mode": "webhook", "avatar": "no"})
    return f"{scheme}://{authority}/?{query}"


def test_rocketchat_webhook(webhook_url: str, host_info: str | None = None) -> None:
    """Отправляет тестовое уведомление в Rocket.Chat через Apprise.

    Args:
        webhook_url: URL входящего вебхука Rocket.Chat.
        host_info: Имя компьютера или идентификатор хранилища.

    Raises:
        ValueError: Если некорректен формат вебхука.
        RuntimeError: Если отправка сообщения завершилась ошибкой.
    """
    from certificate_analyzer.infrastructure.notifications.apprise_backend import AppriseNotificationBackend
    from certificate_analyzer.infrastructure.notifications.message_builder import NotificationMessageBuilder

    apprise_url: str = rocketchat_apprise_url(webhook_url)
    backend: AppriseNotificationBackend = AppriseNotificationBackend([apprise_url])
    msg = NotificationMessageBuilder.test_connection("Rocket.Chat", host_info=host_info)
    backend.send(
        title=msg.title,
        message=msg.message,
        notification_type=msg.notification_type,
    )
