from datetime import UTC, datetime

from backend.domain.planner import plan
from backend.domain.planning import ChapterToPlan, FreeSlot, StudySettings


def test_splits_chapter_by_max_session_and_inserts_break() -> None:
    result = plan(
        [ChapterToPlan(chapter_id=1, minutes_remaining=120)],
        [
            FreeSlot(
                datetime(2026, 11, 9, 9, tzinfo=UTC),
                datetime(2026, 11, 9, 13, tzinfo=UTC),
            )
        ],
        StudySettings(max_session_min=60, break_min=15),
        datetime(2026, 11, 9, 8, tzinfo=UTC),
    )

    assert result.is_feasible
    assert [(item.starts_at.hour, item.starts_at.minute, item.ends_at.hour, item.ends_at.minute)
            for item in result.sessions] == [(9, 0, 10, 0), (10, 15, 11, 15)]


def test_earliest_deadline_is_scheduled_first() -> None:
    result = plan(
        [
            ChapterToPlan(
                chapter_id=1,
                minutes_remaining=30,
                deadline_due_at=datetime(2026, 11, 9, 12, tzinfo=UTC),
            ),
            ChapterToPlan(
                chapter_id=2,
                minutes_remaining=30,
                deadline_due_at=datetime(2026, 11, 9, 10, tzinfo=UTC),
            ),
        ],
        [
            FreeSlot(
                datetime(2026, 11, 9, 9, tzinfo=UTC),
                datetime(2026, 11, 9, 11, tzinfo=UTC),
            )
        ],
        StudySettings(max_session_min=60, break_min=0),
        datetime(2026, 11, 9, 8, tzinfo=UTC),
    )

    assert result.is_feasible
    assert [item.chapter_id for item in result.sessions] == [2, 1]
    assert result.sessions[0].ends_at == datetime(2026, 11, 9, 9, 30, tzinfo=UTC)


def test_infeasible_plan_returns_shortfall_without_partial_sessions() -> None:
    result = plan(
        [
            ChapterToPlan(
                chapter_id=4,
                minutes_remaining=90,
                deadline_due_at=datetime(2026, 11, 9, 10, tzinfo=UTC),
                deadline_id=7,
                deadline_title="Examen",
            )
        ],
        [
            FreeSlot(
                datetime(2026, 11, 9, 9, tzinfo=UTC),
                datetime(2026, 11, 9, 10, tzinfo=UTC),
            )
        ],
        StudySettings(max_session_min=60, break_min=15),
        datetime(2026, 11, 9, 8, tzinfo=UTC),
    )

    assert not result.is_feasible
    assert result.sessions == ()
    assert len(result.shortfalls) == 1
    assert result.shortfalls[0].missing_min == 30
    assert result.shortfalls[0].deadline_id == 7


def test_study_that_cannot_finish_before_deadline_is_not_scheduled() -> None:
    result = plan(
        [
            ChapterToPlan(
                chapter_id=1,
                minutes_remaining=45,
                deadline_due_at=datetime(2026, 11, 9, 9, 30, tzinfo=UTC),
            )
        ],
        [
            FreeSlot(
                datetime(2026, 11, 9, 9, tzinfo=UTC),
                datetime(2026, 11, 9, 10, tzinfo=UTC),
            )
        ],
        StudySettings(max_session_min=60, break_min=0),
        datetime(2026, 11, 9, 8, tzinfo=UTC),
    )

    assert not result.is_feasible
    assert result.shortfalls[0].missing_min == 15


def test_naive_now_is_rejected() -> None:
    result_now = datetime(2026, 11, 9, 8)

    try:
        plan([], [], StudySettings(), result_now)
    except ValueError as error:
        assert "fuseau horaire" in str(error)
    else:
        raise AssertionError("Une datetime sans fuseau doit être refusée")