from datetime import datetime

from certificate_analyzer.domain.enums.mchd_status import MchdStatus


def mchd_status(valid_to, now=None, warning_days=60):
    today = (now or datetime.now()).date()
    days = (valid_to.date() - today).days
    if days < 0:
        return MchdStatus.EXPIRED
    if days <= warning_days:
        return MchdStatus.EXPIRING_SOON
    return MchdStatus.ACTIVE
