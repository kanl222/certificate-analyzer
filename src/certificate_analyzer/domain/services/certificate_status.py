from datetime import UTC, datetime, timedelta

from certificate_analyzer.domain.enums.certificate_status import CertificateStatus


def utc(value):
    return (
        value.replace(tzinfo=UTC)
        if value.tzinfo is None
        else value.astimezone(UTC)
    )


def certificate_status(valid_from, valid_to, now=None, warning_days=60):
    now = utc(now or datetime.now(UTC))
    start, end = utc(valid_from), utc(valid_to)
    if end < start or now < start:
        return CertificateStatus.INVALID
    if now >= end:
        return CertificateStatus.EXPIRED
    if end - now <= timedelta(days=warning_days):
        return CertificateStatus.EXPIRING_SOON
    return CertificateStatus.ACTIVE
