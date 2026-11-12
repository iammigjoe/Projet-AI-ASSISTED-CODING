"""
===============================================================================
Tests : login_throttle
===============================================================================
Objectif :
    Vérifier l'attente exponentielle après des échecs de connexion, son plafond,
    sa remise à zéro, et l'absence de blocage définitif.

Lot :
    A (socle et sécurité)
===============================================================================
"""

from datetime import UTC, datetime, timedelta

from backend.core import login_throttle
from backend.core.login_throttle import FREE_ATTEMPTS, MAX_DELAY, RESET_AFTER, LoginThrottle

NOW = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
KEYS = ("email:alice@exemple.fr", "ip:203.0.113.7")


def _fail(throttle: LoginThrottle, times: int, at: datetime = NOW) -> None:
    for _ in range(times):
        throttle.record_failure(KEYS, at)


def test_free_attempts_require_no_wait():
    throttle = LoginThrottle()
    _fail(throttle, FREE_ATTEMPTS - 1)

    assert throttle.retry_after(KEYS, NOW) == 0


def test_wait_starts_after_free_attempts_and_doubles():
    throttle = LoginThrottle()
    _fail(throttle, FREE_ATTEMPTS)
    first_wait = throttle.retry_after(KEYS, NOW)
    _fail(throttle, 1)
    second_wait = throttle.retry_after(KEYS, NOW)

    assert first_wait == 30
    assert second_wait == 60


def test_wait_is_capped():
    throttle = LoginThrottle()
    _fail(throttle, FREE_ATTEMPTS + 20)

    assert throttle.retry_after(KEYS, NOW) == MAX_DELAY.total_seconds()


def test_wait_decreases_with_time_and_ends():
    throttle = LoginThrottle()
    _fail(throttle, FREE_ATTEMPTS)

    assert throttle.retry_after(KEYS, NOW + timedelta(seconds=20)) == 10
    assert throttle.retry_after(KEYS, NOW + timedelta(seconds=31)) == 0


def test_success_forgets_failures():
    throttle = LoginThrottle()
    _fail(throttle, FREE_ATTEMPTS + 3)
    throttle.record_success(KEYS)

    assert throttle.retry_after(KEYS, NOW) == 0


def test_failures_are_forgotten_after_reset_period():
    throttle = LoginThrottle()
    _fail(throttle, FREE_ATTEMPTS + 3)
    later = NOW + RESET_AFTER + timedelta(seconds=1)

    assert throttle.retry_after(KEYS, later) == 0
    throttle.record_failure(KEYS, later)
    assert throttle.retry_after(KEYS, later) == 0


def test_attacks_from_one_ip_slow_down_any_email_from_that_ip():
    throttle = LoginThrottle()
    for index in range(FREE_ATTEMPTS):
        throttle.record_failure((f"email:user{index}@exemple.fr", "ip:203.0.113.7"), NOW)

    assert throttle.retry_after(("email:new@exemple.fr", "ip:203.0.113.7"), NOW) > 0
    assert throttle.retry_after(("email:new@exemple.fr", "ip:198.51.100.1"), NOW) == 0


def test_tracked_keys_are_bounded(monkeypatch):
    monkeypatch.setattr(login_throttle, "MAX_TRACKED_KEYS", 3)
    throttle = LoginThrottle()
    for index in range(10):
        throttle.record_failure((f"ip:10.0.0.{index}",), NOW + timedelta(seconds=index))

    assert len(throttle._records) == 3
