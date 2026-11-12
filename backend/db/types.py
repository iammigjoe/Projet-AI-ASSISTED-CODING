"""
===============================================================================
Module : types
===============================================================================
Objectif :
    Types de colonnes qui stockent les dates et heures dans SQLite sans perdre
    ni le fuseau ni l'ordre.

Responsabilités :
    - UtcDateTime : instant toujours en UTC ; refuse une datetime sans fuseau.
    - LocalTime : heure locale récurrente « HH:MM », sans date ni fuseau.
    - Garantir un texte de largeur fixe : l'ordre alphabétique est l'ordre
      chronologique, donc ORDER BY et les comparaisons restent justes.

Utilisé par :
    Les modèles de backend/db/models (toutes les colonnes _at et _local).

Exemple d'utilisation :
    starts_at: Mapped[datetime] = mapped_column(UtcDateTime)
    starts_local: Mapped[time] = mapped_column(LocalTime)

Lot :
    A (socle et sécurité)
===============================================================================
"""

from datetime import UTC, datetime, time

from sqlalchemy import String
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

# =============================================================================
# Constantes
# =============================================================================

UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
LOCAL_TIME_FORMAT = "%H:%M"

# =============================================================================
# API publique
# =============================================================================


class UtcDateTime(TypeDecorator[datetime]):
    """Instant stocké en texte ISO 8601 UTC (« 2026-11-12T17:00:00Z »).

    SQLite n'a pas de type date : le DateTime standard de SQLAlchemy y écrit
    un texte sans fuseau, et un instant écrit en heure de Paris serait relu
    comme de l'UTC sans erreur (modele_donnees.md §5). Ce type l'interdit.
    Les microsecondes ne sont pas conservées : aucune donnée de MyPlan n'en a
    besoin, et la largeur fixe garde le tri alphabétique juste.
    """

    impl = String(20)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> str | None:
        """Convertit en UTC et formate ; refuse une datetime sans fuseau.

        Raises:
            ValueError: Si la datetime n'a pas de fuseau.
        """
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                f"datetime sans fuseau refusée : {value!r} (utiliser datetime.now(UTC))"
            )
        return value.astimezone(UTC).strftime(UTC_FORMAT)

    def process_result_value(self, value: str | None, dialect: Dialect) -> datetime | None:
        """Relit le texte stocké en datetime avec tzinfo=UTC."""
        if value is None:
            return None
        return datetime.strptime(value, UTC_FORMAT).replace(tzinfo=UTC)


class LocalTime(TypeDecorator[time]):
    """Heure locale récurrente stockée en « HH:MM » (disponibilités, exceptions).

    Ce n'est pas un instant : « 18:00 » reste 18:00 à l'heure de l'étudiant
    toute l'année, changements d'heure compris (modele_donnees.md §5).
    """

    impl = String(5)
    cache_ok = True

    def process_bind_param(self, value: time | None, dialect: Dialect) -> str | None:
        """Formate en « HH:MM » ; refuse un fuseau ou des secondes.

        Raises:
            ValueError: Si l'heure porte un fuseau ou des secondes.
        """
        if value is None:
            return None
        if value.tzinfo is not None:
            raise ValueError(f"heure locale avec fuseau refusée : {value!r}")
        if value.second or value.microsecond:
            raise ValueError(f"heure locale à la minute près attendue : {value!r}")
        return value.strftime(LOCAL_TIME_FORMAT)

    def process_result_value(self, value: str | None, dialect: Dialect) -> time | None:
        """Relit « HH:MM » en time sans fuseau."""
        if value is None:
            return None
        return datetime.strptime(value, LOCAL_TIME_FORMAT).time()  # noqa: DTZ007  # heure locale voulue


def utc_now() -> datetime:
    """Renvoie l'instant présent en UTC, à la seconde.

    Sert de valeur par défaut aux colonnes created_at et updated_at. Les
    services, eux, reçoivent l'heure par l'horloge injectée (core/clock).
    """
    return datetime.now(UTC).replace(microsecond=0)
