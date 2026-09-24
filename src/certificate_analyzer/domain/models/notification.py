"""Доменная модель уведомления."""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from certificate_analyzer.domain.enums.notification_type import NotificationType


@dataclass(slots=True)
class Notification:
    """Доменная модель уведомления."""

    title: str
    message: str
    notification_type: NotificationType = NotificationType.INFO
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Преобразование уведомления в словарь для сериализации."""
        res = asdict(self)
        res["notification_type"] = self.notification_type.value
        res["timestamp"] = self.timestamp.isoformat()
        return res
