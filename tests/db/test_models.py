"""
===============================================================================
Tests : models
===============================================================================
Objectif :
    Vérifier que les règles portées par la base tiennent : contraintes CHECK,
    unicités, index partiel du planning actif (RG6), cascades de suppression.

Lot :
    A (socle et sécurité)
===============================================================================
"""

from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, StatementError

from backend.db.models import (
    Availability,
    Chapter,
    Course,
    Deadline,
    Document,
    Plan,
    StudySession,
    User,
    UserSettings,
)
from backend.domain.enums import (
    DeadlineType,
    DocumentType,
    PlanOrigin,
    PlanStatus,
    SessionStatus,
)

START = datetime(2026, 11, 16, 17, 0, tzinfo=UTC)

# =============================================================================
# Fonctions internes
# =============================================================================


def _user(session, email="etudiant@exemple.fr") -> User:
    user = User(email=email, password_hash="argon2-hash")
    session.add(user)
    session.flush()
    return user


def _course(session, user, name="Analyse 2") -> Course:
    course = Course(user_id=user.id, name=name, color="#3366FF")
    session.add(course)
    session.flush()
    return course


def _chapter(session, course) -> Chapter:
    document = Document(
        course_id=course.id,
        filename_original="cours.pdf",
        storage_key="3f2a.pdf",
        type=DocumentType.PDF,
        size_bytes=1024,
        sha256="a" * 64,
        uploaded_at=START,
    )
    session.add(document)
    session.flush()
    chapter = Chapter(
        document_id=document.id, title="Intégrales", position=0, word_count=4000, estimated_min=30
    )
    session.add(chapter)
    session.flush()
    return chapter


def _plan(session, user, version=1, status=PlanStatus.DRAFT, week="2026-W47") -> Plan:
    plan = Plan(
        user_id=user.id, version=version, week=week, status=status, origin=PlanOrigin.GENERATED
    )
    session.add(plan)
    session.flush()
    return plan


# =============================================================================
# Utilisateurs et paramètres
# =============================================================================


def test_user_email_with_uppercase_is_rejected(db_session):
    with pytest.raises(IntegrityError, match="ck_users_email_lowercase"):
        _user(db_session, email="Etudiant@Exemple.fr")


def test_user_gets_default_timezone_and_timestamps(db_session):
    user = _user(db_session)

    assert user.timezone == "Europe/Paris"
    assert user.created_at.tzinfo is UTC


def test_user_settings_defaults_match_spec(db_session):
    user = _user(db_session)
    settings = UserSettings(user_id=user.id)
    db_session.add(settings)
    db_session.flush()

    assert (settings.reading_speed_wpm, settings.session_minutes, settings.break_min) == (
        200,
        60,
        0,
    )
    assert settings.mastery_goal == "standard"
    assert settings.notif_prefs == {}


def test_user_settings_with_session_too_long_is_rejected(db_session):
    user = _user(db_session)
    db_session.add(UserSettings(user_id=user.id, session_minutes=300))

    with pytest.raises(IntegrityError, match="session_minutes_range"):
        db_session.flush()


# =============================================================================
# Matières
# =============================================================================


def test_course_with_invalid_color_is_rejected(db_session):
    user = _user(db_session)
    db_session.add(Course(user_id=user.id, name="Physique", color="blue"))

    with pytest.raises(IntegrityError, match="color_hex"):
        db_session.flush()


def test_course_name_is_unique_per_user_only(db_session):
    alice = _user(db_session, "alice@exemple.fr")
    bob = _user(db_session, "bob@exemple.fr")
    _course(db_session, alice, "Analyse 2")
    _course(db_session, bob, "Analyse 2")

    with pytest.raises(IntegrityError, match="courses.user_id, courses.name"):
        _course(db_session, alice, "Analyse 2")


# =============================================================================
# Chapitres, disponibilités
# =============================================================================


def test_chapter_effective_min_prefers_override(db_session):
    chapter = _chapter(db_session, _course(db_session, _user(db_session)))

    assert chapter.effective_min == 30
    chapter.estimated_min_override = 45
    assert chapter.effective_min == 45


def test_availability_ending_before_start_is_rejected(db_session):
    user = _user(db_session)
    db_session.add(
        Availability(user_id=user.id, weekday=0, starts_local=time(20, 0), ends_local=time(18, 0))
    )

    with pytest.raises(IntegrityError, match="ends_after_starts"):
        db_session.flush()


# =============================================================================
# Plannings et sessions
# =============================================================================


def test_second_active_plan_for_same_week_is_rejected(db_session):
    user = _user(db_session)
    _plan(db_session, user, version=1, status=PlanStatus.ACTIVE)

    with pytest.raises(IntegrityError, match="plans.user_id, plans.week"):
        _plan(db_session, user, version=2, status=PlanStatus.ACTIVE)


def test_active_plans_of_different_weeks_coexist(db_session):
    user = _user(db_session)
    _plan(db_session, user, version=1, status=PlanStatus.ACTIVE, week="2026-W47")
    _plan(db_session, user, version=2, status=PlanStatus.ACTIVE, week="2026-W48")

    assert db_session.scalar(select(func.count()).select_from(Plan)) == 2


def test_badly_formatted_week_is_rejected(db_session):
    user = _user(db_session)

    with pytest.raises(IntegrityError, match="week_format"):
        _plan(db_session, user, week="2026-47")


def test_each_user_can_have_one_active_plan(db_session):
    alice = _user(db_session, "alice@exemple.fr")
    bob = _user(db_session, "bob@exemple.fr")
    _plan(db_session, alice, status=PlanStatus.ACTIVE)
    _plan(db_session, bob, status=PlanStatus.ACTIVE)
    _plan(db_session, alice, version=2, status=PlanStatus.ARCHIVED)

    assert db_session.scalar(select(func.count()).select_from(Plan)) == 3


def test_self_rating_on_planned_session_is_rejected(db_session):
    user = _user(db_session)
    chapter = _chapter(db_session, _course(db_session, user))
    plan = _plan(db_session, user)
    db_session.add(
        StudySession(
            plan_id=plan.id,
            chapter_id=chapter.id,
            starts_at=START,
            ends_at=START + timedelta(minutes=45),
            self_rating=4,
        )
    )

    with pytest.raises(IntegrityError, match="rating_when_done"):
        db_session.flush()


def test_session_status_is_stored_as_lowercase_value(db_session):
    user = _user(db_session)
    chapter = _chapter(db_session, _course(db_session, user))
    plan = _plan(db_session, user)
    db_session.add(
        StudySession(
            plan_id=plan.id,
            chapter_id=chapter.id,
            starts_at=START,
            ends_at=START + timedelta(minutes=45),
            status=SessionStatus.DONE,
            self_rating=4,
        )
    )
    db_session.flush()

    assert db_session.execute(text("SELECT status FROM study_sessions")).scalar_one() == "done"


def test_unknown_enum_value_is_rejected(db_session):
    user = _user(db_session)
    db_session.add(
        Plan(user_id=user.id, version=1, week="2026-W47", status="finished", origin="generated")
    )

    with pytest.raises(StatementError):
        db_session.flush()


# =============================================================================
# Cascades
# =============================================================================


def test_deleting_user_deletes_everything_below(db_session):
    user = _user(db_session)
    chapter = _chapter(db_session, _course(db_session, user))
    plan = _plan(db_session, user)
    db_session.add(
        StudySession(
            plan_id=plan.id,
            chapter_id=chapter.id,
            starts_at=START,
            ends_at=START + timedelta(minutes=45),
        )
    )
    db_session.flush()

    db_session.execute(text("DELETE FROM users"))

    for table in ("courses", "documents", "chapters", "plans", "study_sessions"):
        remaining = db_session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()  # noqa: S608
        assert remaining == 0, table


# =============================================================================
# Échéances
# =============================================================================


def test_deadline_weight_above_100_is_rejected(db_session):
    user = _user(db_session)
    course = _course(db_session, user)
    db_session.add(
        Deadline(
            user_id=user.id,
            course_id=course.id,
            title="Partiel",
            type=DeadlineType.EXAM,
            due_date=date(2026, 11, 27),
            weight=120,
        )
    )

    with pytest.raises(IntegrityError, match="weight_range"):
        db_session.flush()


def test_deadline_type_outside_contract_is_rejected(db_session):
    user = _user(db_session)
    course = _course(db_session, user)
    db_session.add(
        Deadline(
            user_id=user.id,
            course_id=course.id,
            title="Projet",
            type="project",
            due_date=date(2026, 11, 27),
            weight=50,
        )
    )

    with pytest.raises(StatementError):
        db_session.flush()
