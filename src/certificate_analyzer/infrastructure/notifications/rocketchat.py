"""Convert a Rocket.Chat Incoming Webhook to the existing Apprise transport."""

from urllib.parse import urlencode, urlsplit


def rocketchat_apprise_url(webhook):
    """Accept the standard /hooks/{integrationId}/{token} URL without contacting it."""
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
