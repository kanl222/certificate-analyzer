from datetime import datetime, timedelta, timezone
import pytest
from certificate_analyzer.domain.services.certificate_status import certificate_status
from certificate_analyzer.domain.services.mchd_status import mchd_status


@pytest.mark.parametrize(
    "delta,expected",
    [(0, "EXPIRED"), (-1, "EXPIRED"), (60, "EXPIRING_SOON"), (61, "ACTIVE")],
)
def test_expiration_boundary(delta, expected):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert (
        certificate_status(
            now - timedelta(days=1), now + timedelta(days=delta), now
        ).value
        == expected
    )


def test_timezone_and_future_validity():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    local = now.astimezone(timezone(timedelta(hours=5)))
    assert certificate_status(now - timedelta(days=1), local, now).value == "EXPIRED"
    assert (
        certificate_status(now + timedelta(days=1), now + timedelta(days=10), now).value
        == "INVALID"
    )


def test_mchd_valid_through_expiry_day():
    assert (
        mchd_status(datetime(2026, 1, 1), datetime(2026, 1, 1, 23, 59)).value
        == "EXPIRING_SOON"
    )
