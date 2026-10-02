import logging


class LoggingNotificationBackend:
    def send(self, title, message, notification_type="info", **metadata):
        logging.getLogger(__name__).info("%s: %s", title, message)
