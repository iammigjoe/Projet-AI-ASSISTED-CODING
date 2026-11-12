from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.domain.planning import (
    ChapterToPlan,
    FreeSlot,
    PlanResult,
    PlanShortfall,
    PlannedSession,
    StudySettings,
)


def plan(
    chapters: list[ChapterToPlan] | tuple[ChapterToPlan, ...],
    free_slots: list[FreeSlot] | tuple[FreeSlot, ...],
    settings: StudySettings,
    now: datetime,
) -> PlanResult:
    """Schedule chapters by earliest deadline, splitting long work into sessions."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now doit inclure un fuseau horaire")
    now_utc = now.astimezone(UTC)

    remaining_slots = [
        [max(slot.starts_at.astimezone(UTC), now_utc), slot.ends_at.astimezone(UTC)]
        for slot in sorted(free_slots, key=lambda item: item.starts_at)
        if slot.ends_at.astimezone(UTC) > now_utc
    ]
    ordered_chapters = sorted(
        chapters,
        key=lambda chapter: (
            chapter.deadline_due_at is None,
            chapter.deadline_due_at.astimezone(UTC)
            if chapter.deadline_due_at is not None
            else datetime.max.replace(tzinfo=UTC),
            -chapter.importance,
            chapter.chapter_id,
        ),
    )

    sessions: list[PlannedSession] = []
    shortfalls: list[PlanShortfall] = []
    next_session_at = now_utc

    for chapter in ordered_chapters:
        remaining_min = chapter.minutes_remaining
        if remaining_min == 0:
            continue
        deadline = (
            chapter.deadline_due_at.astimezone(UTC)
            if chapter.deadline_due_at is not None
            else None
        )
        chapter_minutes_scheduled = 0

        for slot in remaining_slots:
            if remaining_min == 0:
                break
            slot_start, slot_end = slot
            start = max(slot_start, next_session_at)
            if deadline is not None:
                slot_end = min(slot_end, deadline)
            if start >= slot_end:
                continue

            available_min = int((slot_end - start).total_seconds() // 60)
            if available_min <= 0:
                continue
            duration_min = min(
                remaining_min, settings.max_session_min, available_min
            )
            end = start + timedelta(minutes=duration_min)
            sessions.append(PlannedSession(chapter.chapter_id, start, end))
            remaining_min -= duration_min
            chapter_minutes_scheduled += duration_min
            next_session_at = end + timedelta(minutes=settings.break_min)
            slot[0] = next_session_at

        if remaining_min:
            shortfalls.append(
                PlanShortfall(
                    chapter_id=chapter.chapter_id,
                    missing_min=remaining_min,
                    deadline_due_at=deadline,
                    deadline_id=chapter.deadline_id,
                    deadline_title=chapter.deadline_title,
                )
            )

    if shortfalls:
        return PlanResult(sessions=(), shortfalls=tuple(shortfalls))
    return PlanResult(sessions=tuple(sessions))