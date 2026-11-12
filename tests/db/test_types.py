"""
===============================================================================
Tests : types
===============================================================================
Objectif :
    Vérifier que UtcDateTime et LocalTime refusent ce qui serait relu faux, et
    que le texte stocké garde l'ordre chronologique.

Lot :
    A (socle et sécurité)
===============================================================================
"""

from datetime import UTC, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, insert, select, text
from sqlalchemy.exc import StatementError

from backend.db.session import make_engine
from backend.db.types import LocalTime, UtcDateTime

PARIS = ZoneInfo("Europe/Paris")


@pytest.fixture
def table_and_engine():
    metadata = MetaData()
    table = Table(
        "samples",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("at", UtcDateTime),
        Column("local", LocalTime),
    )
    engine = make_engine("sqlite://")
    metadata.create_all(engine)
    return table, engine


def test_utc_datetime_with_naive_value_raises(table_and_engine):
    table, engine = table_and_engine

    with engine.begin() as connection, pytest.raises(StatementError, match="sans fuseau"):
        connection.execute(insert(table).values(at=datetime(2026, 11, 12, 18, 0)))  # noqa: DTZ001


def test_utc_datetime_converts_paris_time_to_utc(table_and_engine):
    table, engine = table_and_engine
    paris_evening = datetime(2026, 11, 12, 18, 0, tzinfo=PARIS)  # UTC+1 en novembre

    with engine.begin() as connection:
        connection.execute(insert(table).values(id=1, at=paris_evening))
        stored = connection.execute(text("SELECT at FROM samples")).scalar_one()
        read = connection.execute(select(table.c.at)).scalar_one()

    assert stored == "2026-11-12T17:00:00Z"
    assert read == paris_evening
    assert read.tzinfo is UTC


def test_utc_datetime_text_sorts_chronologically(table_and_engine):
    table, engine = table_and_engine
    base = datetime(2026, 3, 29, 0, 30, tzinfo=UTC)
    instants = [base + timedelta(hours=hours) for hours in (5, 0, 23, 1)]

    with engine.begin() as connection:
        for index, instant in enumerate(instants):
            connection.execute(insert(table).values(id=index, at=instant))
        ordered = connection.execute(select(table.c.at).order_by(table.c.at)).scalars().all()

    assert ordered == sorted(instants)


def test_utc_datetime_accepts_any_fixed_offset(table_and_engine):
    table, engine = table_and_engine
    new_york = datetime(2026, 7, 1, 8, 0, tzinfo=timezone(timedelta(hours=-4)))

    with engine.begin() as connection:
        connection.execute(insert(table).values(id=1, at=new_york))
        read = connection.execute(select(table.c.at)).scalar_one()

    assert read == datetime(2026, 7, 1, 12, 0, tzinfo=UTC)


def test_local_time_round_trips_as_hh_mm(table_and_engine):
    table, engine = table_and_engine

    with engine.begin() as connection:
        connection.execute(insert(table).values(id=1, local=time(18, 0)))
        stored = connection.execute(text("SELECT local FROM samples")).scalar_one()
        read = connection.execute(select(table.c.local)).scalar_one()

    assert stored == "18:00"
    assert read == time(18, 0)


def test_local_time_with_timezone_raises(table_and_engine):
    table, engine = table_and_engine

    with engine.begin() as connection, pytest.raises(StatementError, match="fuseau"):
        connection.execute(insert(table).values(local=time(18, 0, tzinfo=UTC)))


def test_local_time_with_seconds_raises(table_and_engine):
    table, engine = table_and_engine

    with engine.begin() as connection, pytest.raises(StatementError, match="minute"):
        connection.execute(insert(table).values(local=time(18, 0, 30)))
