"""
===============================================================================
Tests : password_policy
===============================================================================
Objectif :
    Vérifier que la politique refuse les mots de passe faibles, et accepte une
    phrase de passe longue.

Lot :
    A (socle et sécurité)
===============================================================================
"""

import pytest

from backend.domain.password_policy import MAX_LENGTH, password_problems


def test_long_passphrase_is_accepted():
    assert password_problems("cheval correct pile agrafe", email="alice@exemple.fr") == []


@pytest.mark.parametrize(
    ("password", "expected"),
    [
        ("court1!", "au moins 12"),
        ("a" * (MAX_LENGTH + 1), "au plus 128"),
        ("aaaaaaaaaaaaaa", "un seul caractère"),
        ("Motdepasse123", "plus utilisés"),
        ("AZERTYUIOP12", "plus utilisés"),
    ],
)
def test_weak_passwords_are_refused(password, expected):
    problems = password_problems(password)

    assert any(expected in problem for problem in problems), problems


def test_password_containing_email_identifier_is_refused():
    problems = password_problems("alice.martin-2026!", email="alice.martin@exemple.fr")

    assert any("identifiant" in problem for problem in problems)


def test_short_email_identifier_is_not_checked():
    assert password_problems("une phrase bien longue", email="al@exemple.fr") == []
