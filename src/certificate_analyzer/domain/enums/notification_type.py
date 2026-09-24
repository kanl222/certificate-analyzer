from enum import Enum


class NotificationType(str, Enum):
    """Типы уведомлений в системе."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
