from datetime import datetime

from certificate_analyzer.domain.enums.mchd_status import MchdStatus


def mchd_status(valid_to, now=None, warning_days=60, *, valid_from=None):
    today = (now or datetime.now()).date()
    if valid_from is not None and (valid_from.date() > today or valid_to < valid_from):
        return MchdStatus.INVALID
    days = (valid_to.date() - today).days
    if days < 0:
        return MchdStatus.EXPIRED
    if days <= warning_days:
        return MchdStatus.EXPIRING_SOON
    return MchdStatus.ACTIVE
