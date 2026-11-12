"""
===============================================================================
Domaine : enums
===============================================================================
Objectif :
    Déclarer toute valeur à ensemble fini du projet : statuts, types, catégories.

Responsabilités :
    - Une seule source pour chaque liste de valeurs : les contraintes CHECK de
      la base sont construites à partir d'ici (backend/db/base.py, enum_type).
    - Valeurs en snake_case, stables : elles sont stockées en base et exposées
      par l'API.

Pur :
    Aucun import en dehors de la bibliothèque standard.

Utilisé par :
    Les modèles, les schémas Pydantic, le domaine et les services de tous les lots.

Exemple d'utilisation :
    if study_session.status is SessionStatus.DONE: ...

Lot :
    A (socle et sécurité) ; chaque lot ajoute ses énumérations à la fin de sa
    section, sans réorganiser celles des autres (repartition_taches.md §5).
===============================================================================
"""

from enum import StrEnum

# =============================================================================
# Lot A : socle et sécurité
# =============================================================================


class MasteryGoal(StrEnum):
    """Niveau de maîtrise visé : donne le coefficient d'objectif (P0-07)."""

    DISCOVERY = "discovery"
    STANDARD = "standard"
    MASTERY = "mastery"


# =============================================================================
# Lot B : ingestion
# =============================================================================


class DocumentType(StrEnum):
    """Format d'un document, déduit des magic bytes, jamais de l'extension."""

    PDF = "pdf"
    MARKDOWN = "markdown"


class DocumentStatus(StrEnum):
    """Avancement de l'extraction d'un document (P1-06)."""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


# =============================================================================
# Lot C : planification
# =============================================================================


class ExceptionKind(StrEnum):
    """Nature d'une exception aux disponibilités (P0-09)."""

    BLOCKED = "blocked"
    ADDED = "added"


class DeadlineType(StrEnum):
    """Nature d'une échéance (P0-10)."""

    EXAM = "exam"
    PROJECT = "project"


class PlanStatus(StrEnum):
    """Cycle de vie d'une version de planning ; une seule active par utilisateur (RG6)."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class PlanOrigin(StrEnum):
    """Ce qui a produit une version de planning (P1-08)."""

    GENERATED = "generated"
    REPLANNED = "replanned"


# =============================================================================
# Lot D : agenda et suivi
# =============================================================================


class SessionStatus(StrEnum):
    """État d'une session d'étude (P0-13, RG9)."""

    PLANNED = "planned"
    DONE = "done"
    MISSED = "missed"


class SessionKind(StrEnum):
    """Session d'étude d'un chapitre, ou révision espacée (P2-06)."""

    STUDY = "study"
    REVIEW = "review"
