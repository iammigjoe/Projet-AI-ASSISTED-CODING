from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Literal


@dataclass(frozen=True)
class AvailabilityRule:
    weekday: int
    starts_local: time
    ends_local: time
    valid_from: date
    valid_to: date | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.weekday <= 6:
            raise ValueError("weekday doit être compris entre 0 et 6")
        if self.starts_local >= self.ends_local:
            raise ValueError("ends_local doit être après starts_local")
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to ne peut pas précéder valid_from")


@dataclass(frozen=True)
class AvailabilityException:
    date: date
    kind: Literal["blocked", "added"]
    starts_local: time | None = None
    ends_local: time | None = None

    def __post_init__(self) -> None:
        if self.kind not in ("blocked", "added"):
            raise ValueError("kind doit être 'blocked' ou 'added'")
        if (self.starts_local is None) != (self.ends_local is None):
            raise ValueError("starts_local et ends_local doivent être fournis ensemble")
        if self.kind == "added" and self.starts_local is None:
            raise ValueError("Une exception 'added' doit avoir des heures")
        if (
            self.starts_local is not None
            and self.ends_local is not None
            and self.starts_local >= self.ends_local
        ):
            raise ValueError("ends_local doit être après starts_local")


@dataclass(frozen=True)
class BusyInterval:
    starts_at: datetime
    ends_at: datetime

    def __post_init__(self) -> None:
        _validate_aware_interval(self.starts_at, self.ends_at)


@dataclass(frozen=True)
class FreeSlot:
    starts_at: datetime
    ends_at: datetime

    def __post_init__(self) -> None:
        _validate_aware_interval(self.starts_at, self.ends_at)


@dataclass(frozen=True)
class ChapterToPlan:
    chapter_id: int
    minutes_remaining: int
    deadline_due_at: datetime | None = None
    deadline_id: int | None = None
    deadline_title: str | None = None
    importance: int = 2

    def __post_init__(self) -> None:
        if self.chapter_id <= 0:
            raise ValueError("chapter_id doit être positif")
        if self.minutes_remaining < 0:
            raise ValueError("minutes_remaining ne peut pas être négatif")
        if self.deadline_due_at is not None:
            _validate_aware_datetime(self.deadline_due_at)
        if self.deadline_id is not None and self.deadline_id <= 0:
            raise ValueError("deadline_id doit être positif")
        if not 1 <= self.importance <= 3:
            raise ValueError("importance doit être comprise entre 1 et 3")


@dataclass(frozen=True)
class StudySettings:
    max_session_min: int = 90
    break_min: int = 15

    def __post_init__(self) -> None:
        if self.max_session_min <= 0:
            raise ValueError("max_session_min doit être positif")
        if self.break_min < 0:
            raise ValueError("break_min ne peut pas être négatif")


@dataclass(frozen=True)
class PlannedSession:
    chapter_id: int
    starts_at: datetime
    ends_at: datetime

    def __post_init__(self) -> None:
        if self.chapter_id <= 0:
            raise ValueError("chapter_id doit être positif")
        _validate_aware_interval(self.starts_at, self.ends_at)


@dataclass(frozen=True)
class PlanShortfall:
    chapter_id: int
    missing_min: int
    deadline_due_at: datetime | None = None
    deadline_id: int | None = None
    deadline_title: str | None = None


@dataclass(frozen=True)
class PlanResult:
    sessions: tuple[PlannedSession, ...]
    shortfalls: tuple[PlanShortfall, ...] = ()

    @property
    def is_feasible(self) -> bool:
        return not self.shortfalls


def _validate_aware_datetime(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Les dates doivent inclure un fuseau horaire")


def _validate_aware_interval(starts_at: datetime, ends_at: datetime) -> None:
    _validate_aware_datetime(starts_at)
    _validate_aware_datetime(ends_at)
    if ends_at <= starts_at:
        raise ValueError("ends_at doit être après starts_at")