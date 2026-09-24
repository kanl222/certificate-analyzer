import logging
import logging.config
import sys


def setup_logging(level=logging.INFO):
    """Sets up standard logging configuration."""
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": log_format,
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "standard",
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.FileHandler",
                "level": "DEBUG",
                "formatter": "standard",
                "filename": "log.log",
                "mode": "a",
                "encoding": "utf-8",
            }
        },
        "root": {
            "handlers": ["console", "file"],
            "level": level,
        }
    }
    
    logging.config.dictConfig(logging_config)
    logging.info("Logging configured.")
