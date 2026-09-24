import logging


class LoggingNotificationBackend:
    def send(self, title, message):
        logging.getLogger(__name__).info("%s: %s", title, message)
