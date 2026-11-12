from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from backend.domain.planning import (
    AvailabilityException,
    AvailabilityRule,
    BusyInterval,
    FreeSlot,
)


def build_free_slots(
    availabilities: list[AvailabilityRule] | tuple[AvailabilityRule, ...],
    exceptions: list[AvailabilityException] | tuple[AvailabilityException, ...],
    starts_at: datetime,
    ends_at: datetime,
    timezone: str,
    busy_intervals: list[BusyInterval] | tuple[BusyInterval, ...] = (),
) -> tuple[FreeSlot, ...]:
    """Expand local recurring availability and return unoccupied UTC intervals."""
    _validate_aware_interval(starts_at, ends_at)
    try:
        local_zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as error:
        raise ValueError(f"Fuseau horaire inconnu : {timezone}") from error

    period_start = starts_at.astimezone(UTC)
    period_end = ends_at.astimezone(UTC)
    first_date = period_start.astimezone(local_zone).date()
    last_date = period_end.astimezone(local_zone).date()
    available: list[tuple[datetime, datetime]] = []

    current_date = first_date
    while current_date <= last_date:
        for rule in availabilities:
            if (
                current_date.weekday() == rule.weekday
                and current_date >= rule.valid_from
                and (rule.valid_to is None or current_date <= rule.valid_to)
            ):
                interval = _local_interval(
                    current_date, rule.starts_local, rule.ends_local, local_zone
                )
                if interval is not None:
                    available.append(interval)
        current_date += timedelta(days=1)

    blocked: list[tuple[datetime, datetime]] = []
    for exception in exceptions:
        if exception.kind == "added":
            interval = _local_interval(
                exception.date,
                exception.starts_local,
                exception.ends_local,
                local_zone,
            )
            if interval is not None:
                available.append(interval)
        elif exception.starts_local is None:
            interval = _local_interval(
                exception.date, time.min, time.min, local_zone, full_day=True
            )
            if interval is not None:
                blocked.append(interval)
        else:
            interval = _local_interval(
                exception.date,
                exception.starts_local,
                exception.ends_local,
                local_zone,
            )
            if interval is not None:
                blocked.append(interval)

    available = _merge_intervals(
        _clip_interval(interval, period_start, period_end)
        for interval in available
    )
    blocked.extend(
        _clip_interval((item.starts_at, item.ends_at), period_start, period_end)
        for item in busy_intervals
    )
    blocked = _merge_intervals(blocked)

    free: list[tuple[datetime, datetime]] = []
    for starts, ends in available:
        remaining = [(starts, ends)]
        for blocked_start, blocked_end in blocked:
            next_remaining: list[tuple[datetime, datetime]] = []
            for remaining_start, remaining_end in remaining:
                if blocked_end <= remaining_start or blocked_start >= remaining_end:
                    next_remaining.append((remaining_start, remaining_end))
                    continue
                if remaining_start < blocked_start:
                    next_remaining.append((remaining_start, blocked_start))
                if blocked_end < remaining_end:
                    next_remaining.append((blocked_end, remaining_end))
            remaining = next_remaining
        free.extend(remaining)

    return tuple(FreeSlot(start, end) for start, end in _merge_intervals(free))


def _local_interval(
    interval_date: date,
    starts_local: time | None,
    ends_local: time | None,
    timezone: ZoneInfo,
    *,
    full_day: bool = False,
) -> tuple[datetime, datetime] | None:
    if full_day:
        local_start = _resolve_local_datetime(
            datetime.combine(interval_date, time.min), timezone, fold=0
        )
        local_end = _resolve_local_datetime(
            datetime.combine(interval_date + timedelta(days=1), time.min),
            timezone,
            fold=1,
        )
    else:
        assert starts_local is not None and ends_local is not None
        local_start = _resolve_local_datetime(
            datetime.combine(interval_date, starts_local), timezone, fold=0
        )
        local_end = _resolve_local_datetime(
            datetime.combine(interval_date, ends_local), timezone, fold=1
        )
    if local_start is None or local_end is None or local_end <= local_start:
        return None
    return local_start.astimezone(UTC), local_end.astimezone(UTC)


def _resolve_local_datetime(
    value: datetime, timezone: ZoneInfo, *, fold: int
) -> datetime | None:
    localized = value.replace(tzinfo=timezone, fold=fold)
    round_trip = localized.astimezone(UTC).astimezone(timezone).replace(tzinfo=None)
    if round_trip != value:
        return None
    return localized


def _clip_interval(
    interval: tuple[datetime, datetime],
    period_start: datetime,
    period_end: datetime,
) -> tuple[datetime, datetime] | None:
    starts = max(interval[0], period_start)
    ends = min(interval[1], period_end)
    return (starts, ends) if starts < ends else None


def _merge_intervals(
    intervals: object,
) -> list[tuple[datetime, datetime]]:
    valid = sorted(interval for interval in intervals if interval is not None)  # type: ignore[union-attr]
    merged: list[tuple[datetime, datetime]] = []
    for starts, ends in valid:
        if merged and starts <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], ends))
        else:
            merged.append((starts, ends))
    return merged


def _validate_aware_interval(starts_at: datetime, ends_at: datetime) -> None:
    if (
        starts_at.tzinfo is None
        or starts_at.utcoffset() is None
        or ends_at.tzinfo is None
        or ends_at.utcoffset() is None
    ):
        raise ValueError("Les dates doivent inclure un fuseau horaire")
    if ends_at <= starts_at:
        raise ValueError("ends_at doit être après starts_at")