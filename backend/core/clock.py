"""
===============================================================================
Module : clock
===============================================================================
Objectif :
    Horloge injectée dans les services, pour qu'aucun test ne dépende du jour
    où il tourne (diagramme_classes.md §6).

Responsabilités :
    - Fournir l'heure courante en UTC, avec fuseau.
    - Être remplaçable dans les tests par une heure fixe (dependency_overrides).

Utilisé par :
    Les services et les routers, via la dépendance FastAPI get_clock.

Exemple d'utilisation :
    def generate(self, user_id: int, clock: Clock) -> Plan:
        now = clock()

Lot :
    A (socle et sécurité)
===============================================================================
"""

from collections.abc import Callable
from datetime import UTC, datetime

# =============================================================================
# Types
# =============================================================================

Clock = Callable[[], datetime]

# =============================================================================
# API publique
# =============================================================================


def system_clock() -> datetime:
    """Renvoie l'instant présent en UTC."""
    return datetime.now(UTC)


def get_clock() -> Clock:
    """Dépendance FastAPI : l'horloge de l'application, remplacée dans les tests."""
    return system_clock
