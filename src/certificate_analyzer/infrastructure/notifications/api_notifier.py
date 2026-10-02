"""Бэкенд для отправки уведомлений через внешний HTTP API (с поддержкой режима заглушки/stub)."""

import json
import logging
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any
from uuid import uuid4

from certificate_analyzer.infrastructure.notifications.base import NotificationBackend

logger = logging.getLogger(__name__)


class ApiNotificationBackend(NotificationBackend):
    """Бэкенд отправки уведомлений в удаленный API (Webhook, мониторинг, корпоративный мессенджер).

    В режиме stub_mode=True работает как заглушка: валидирует и формирует payload,
    логирует запрос и сохраняет историю для аудита/тестирования без реального обращения к сети.
    """

    def __init__(
        self,
        api_url: str = "https://api.example.com/v1/notifications",
        api_key: str | None = None,
        stub_mode: bool = True,
        timeout: float = 5.0,
        max_response_bytes: int = 65536,
        history_limit: int = 100,
    ) -> None:
        self.api_url = api_url
        self.api_key = api_key
        self.stub_mode = stub_mode
        if max_response_bytes <= 0 or history_limit <= 0:
            raise ValueError("Лимиты ответа и истории должны быть положительными")
        self.max_response_bytes = max_response_bytes
        self.history_limit = history_limit
        self.timeout = timeout
        self.history: list[dict[str, Any]] = []

    def send(self, title: str, message: str, notification_type: str = "info", **kwargs) -> dict[str, Any]:
        """Отправляет уведомление в API либо имитирует отправку в stub-режиме."""
        payload = {
            "notification_id": str(uuid4()),
            "title": title,
            "message": message,
            "type": notification_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "certificate-analyzer",
            "metadata": kwargs,
        }

        if self.stub_mode:
            return self._send_stub(payload)
        return self._send_http(payload)

    def _send_stub(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Эмуляция отправки (заглушка API)."""
        logger.info(
            "[API Notifier STUB] Отправка уведомления на %s: ID=%s, Title='%s', Type='%s'",
            self.api_url,
            payload["notification_id"],
            payload["title"],
            payload["type"],
        )
        logger.debug("[API Notifier STUB] Полный payload: %s", json.dumps(payload, ensure_ascii=False))

        result = {
            "status": "success",
            "mode": "stub",
            "notification_id": payload["notification_id"],
            "url": self.api_url,
            "payload": payload,
        }
        self._remember(result)
        return result

    def _send_http(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Реальная отправка HTTP POST запроса."""
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "CertificateAnalyzer/2.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(self.api_url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read(self.max_response_bytes + 1)
                if len(raw) > self.max_response_bytes:
                    raise ValueError("Ответ API превышает допустимый размер")
                body = raw.decode("utf-8")
                logger.info("[API Notifier] Уведомление успешно отправлено: %s", payload["notification_id"])
                result = {
                    "status": "success",
                    "mode": "live",
                    "code": response.status,
                    "response": body,
                    "notification_id": payload["notification_id"],
                }
                self._remember(result)
                return result
        except urllib.error.URLError as e:
            logger.error("[API Notifier] Ошибка отправки уведомления в API: %s", e)
            result = {
                "status": "error",
                "mode": "live",
                "error": str(e),
                "notification_id": payload["notification_id"],
            }
            self._remember(result)
            return result
        except Exception as e:
            logger.exception("[API Notifier] Непредвиденная ошибка отправки: %s", e)
            result = {
                "status": "error",
                "mode": "live",
                "error": str(e),
                "notification_id": payload["notification_id"],
            }
            self._remember(result)
            return result

    def _remember(self, result: dict[str, Any]) -> None:
        self.history.append(result)
        del self.history[:-self.history_limit]

    def clear_history(self) -> None:
        """Очистка истории отправленных уведомлений."""
        self.history.clear()
