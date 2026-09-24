from pathlib import Path

from certificate_analyzer.infrastructure.config.paths import config_dir
from certificate_analyzer.infrastructure.persistence.json_storage import (
    read_json,
    write_json,
)


class NotificationHistoryStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else config_dir() / "notification_history.json"

    def load(self):
        source = self.path
        if not source.exists():
            source = Path.home() / "notification_history.json"
        data = read_json(source, [])
        if not isinstance(data, list):
            raise ValueError("История уведомлений должна содержать список")
        return [
            item
            for item in data
            if isinstance(item, dict)
            and all(k in item for k in ("time", "message", "type"))
        ][:100]

    def save(self, notifications):
        write_json(self.path, notifications[:100])
