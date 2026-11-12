"""
===============================================================================
Tests : factories
===============================================================================
Objectif :
    Appeler les fabriques de test pour de vrai : une fabrique qui ne suit plus
    le modèle (colonne supprimée, champ renommé) doit échouer ici, pas dans le
    premier test d'un autre lot qui l'utilise.

Lot :
    D (agenda et suivi)
===============================================================================
"""

from datetime import timedelta

import pytest

from backend.domain.enums import SessionStatus
from tests.fixtures.factories import DEFAULT_SESSION_START, make_study_session


def test_make_study_session_builds_a_valid_session():
    session = make_study_session(duration_min=60, status=SessionStatus.DONE, self_rating=4)

    assert session.ends_at - session.starts_at == timedelta(minutes=60)
    assert session.starts_at == DEFAULT_SESSION_START
    assert session.status is SessionStatus.DONE


def test_make_study_session_refuses_non_positive_duration():
    with pytest.raises(ValueError, match="duration_min"):
        make_study_session(duration_min=0)
