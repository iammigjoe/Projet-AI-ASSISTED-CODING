"""
===============================================================================
Tests : conftest
===============================================================================
Objectif :
    Fixtures communes à tous les lots : configuration de test, base SQLite en
    mémoire, client HTTP de l'API.

Responsabilités :
    - Fixer des variables d'environnement de test avant tout import de l'application,
      pour qu'aucun test ne lise le .env d'un développeur.
    - Fournir une base neuve et vide à chaque test.

Lot :
    A (socle et sécurité)
===============================================================================
"""

import os

from cryptography.fernet import Fernet

# =============================================================================
# Environnement de test
# =============================================================================

# Posé avant tout import du backend : get_settings() lit l'environnement une
# seule fois, et un .env de développeur ne doit jamais influencer les tests.
os.environ.update(
    {
        "MYPLAN_ENV": "test",
        "MYPLAN_DATABASE_URL": "sqlite://",
        "MYPLAN_JWT_SECRET_KEY": "test-secret-key-that-is-long-enough-0123456789",
        "MYPLAN_FERNET_KEY": Fernet.generate_key().decode(),
    }
)
