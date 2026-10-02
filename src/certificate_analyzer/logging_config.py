import logging
import sys
from certificate_analyzer.infrastructure.config.paths import config_dir


def setup_logging(level=logging.INFO):
    from concurrent_log_handler import ConcurrentRotatingFileHandler
    folder = config_dir()
    folder.mkdir(parents=True, exist_ok=True)
    handler = ConcurrentRotatingFileHandler(
        str(folder / "application.log"), maxBytes=5 * 1024 * 1024,
        backupCount=3, encoding="utf-8",
    )
    logging.basicConfig(
        level=level,
        handlers=[handler, logging.StreamHandler(sys.stderr)] if sys.stderr else [handler],
        format="%(asctime)s [%(levelname)s] [PID %(process)d] %(name)s: %(message)s",
    )
