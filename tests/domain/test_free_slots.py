from datetime import UTC, date, datetime, time

import pytest

from backend.domain.free_slots import build_free_slots
from backend.domain.planning import AvailabilityException, AvailabilityRule, BusyInterval


def test_recurring_availability_is_converted_to_utc_and_clipped() -> None:
    rule = AvailabilityRule(
        weekday=0,
        starts_local=time(18),
        ends_local=time(20),
        valid_from=date(2026, 11, 9),
    )

    slots = build_free_slots(
        [rule],
        [],
        datetime(2026, 11, 9, 17, 30, tzinfo=UTC),
        datetime(2026, 11, 9, 20, tzinfo=UTC),
        "Europe/Paris",
    )

    assert [(slot.starts_at, slot.ends_at) for slot in slots] == [
        (datetime(2026, 11, 9, 17, tzinfo=UTC), datetime(2026, 11, 9, 19, tzinfo=UTC))
    ]


def test_blocked_exception_and_busy_interval_are_subtracted() -> None:
    rule = AvailabilityRule(
        weekday=0,
        starts_local=time(9),
        ends_local=time(13),
        valid_from=date(2026, 11, 9),
    )
    blocked = AvailabilityException(
        date(2026, 11, 9), "blocked", time(10), time(10, 30)
    )
    busy = BusyInterval(
        datetime(2026, 11, 9, 11, tzinfo=UTC),
        datetime(2026, 11, 9, 11, 30, tzinfo=UTC),
    )

    slots = build_free_slots(
        [rule],
        [blocked],
        datetime(2026, 11, 9, 8, tzinfo=UTC),
        datetime(2026, 11, 9, 13, tzinfo=UTC),
        "UTC",
        [busy],
    )

    assert [
        (slot.starts_at.hour, slot.starts_at.minute, slot.ends_at.hour, slot.ends_at.minute)
        for slot in slots
    ] == [
        (9, 0, 10, 0),
        (10, 30, 11, 0),
        (11, 30, 13, 0),
    ]


def test_added_exception_creates_availability_without_a_weekly_rule() -> None:
    added = AvailabilityException(
        date(2026, 11, 10), "added", time(14), time(16)
    )

    slots = build_free_slots(
        [],
        [added],
        datetime(2026, 11, 10, 0, tzinfo=UTC),
        datetime(2026, 11, 11, 0, tzinfo=UTC),
        "UTC",
    )

    assert len(slots) == 1
    assert slots[0].starts_at == datetime(2026, 11, 10, 14, tzinfo=UTC)
    assert slots[0].ends_at == datetime(2026, 11, 10, 16, tzinfo=UTC)


def test_nonexistent_local_time_during_spring_dst_is_ignored() -> None:
    rule = AvailabilityRule(
        weekday=6,
        starts_local=time(2, 30),
        ends_local=time(4),
        valid_from=date(2026, 3, 29),
        valid_to=date(2026, 3, 29),
    )

    slots = build_free_slots(
        [rule],
        [],
        datetime(2026, 3, 28, tzinfo=UTC),
        datetime(2026, 3, 30, tzinfo=UTC),
        "Europe/Paris",
    )

    assert slots == ()


def test_naive_period_is_rejected() -> None:
    with pytest.raises(ValueError, match="fuseau horaire"):
        build_free_slots(
            [],
            [],
            datetime(2026, 11, 9),
            datetime(2026, 11, 10, tzinfo=UTC),
            "UTC",
        )