"""
===============================================================================
Domaine : errors
===============================================================================
Objectif :
    Erreurs métier, distinctes des erreurs techniques (Spec §4).

Responsabilités :
    - Porter un code stable (UPPER_SNAKE_CASE) et un message en français,
      lisible tel quel par l'étudiant.
    - Ne rien savoir de HTTP : l'API traduit ces erreurs en réponses
      (backend/api/errors.py).

Pur :
    Aucun import en dehors de la bibliothèque standard.

Utilisé par :
    Le domaine et les services de tous les lots.

Exemple d'utilisation :
    raise NotFoundError("Matière introuvable.")

Lot :
    A (socle et sécurité) ; chaque lot ajoute ses erreurs à la fin du fichier,
    avec un code déclaré dans backend/api/errors.py (ErrorCode).
===============================================================================
"""

from typing import Any, ClassVar

# =============================================================================
# API publique
# =============================================================================


class DomainError(Exception):
    """Erreur métier : une règle n'est pas respectée. L'API répond 422 par défaut."""

    code: ClassVar[str] = "DOMAIN_ERROR"

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """Crée l'erreur.

        Args:
            message: Explication en français, affichable telle quelle.
            details: Données structurées utiles au frontend (optionnel).
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(DomainError):
    """Ressource absente, ou appartenant à un autre utilisateur (même réponse : 404)."""

    code: ClassVar[str] = "NOT_FOUND"


class RegistrationClosedError(DomainError):
    """Inscription refusée : le compte unique existe déjà (modele_donnees.md §6.7)."""

    code: ClassVar[str] = "REGISTRATION_CLOSED"


class InvalidCredentialsError(DomainError):
    """Email ou mot de passe incorrect ; même erreur que l'email existe ou non."""

    code: ClassVar[str] = "INVALID_CREDENTIALS"


class TooManyLoginAttemptsError(DomainError):
    """Trop d'échecs de connexion récents : l'essai doit attendre."""

    code: ClassVar[str] = "TOO_MANY_LOGIN_ATTEMPTS"

    def __init__(self, retry_after_seconds: int) -> None:
        """Crée l'erreur.

        Args:
            retry_after_seconds: Attente avant le prochain essai permis.
        """
        super().__init__(
            "Trop de tentatives de connexion. Réessayez dans quelques instants.",
            {"retry_after_seconds": retry_after_seconds},
        )
        self.retry_after_seconds = retry_after_seconds


class WeakPasswordError(DomainError):
    """Mot de passe refusé par la politique (backend/domain/password_policy.py)."""

    code: ClassVar[str] = "WEAK_PASSWORD"  # noqa: S105  # code d'erreur, pas un secret


class ConflictError(DomainError):
    """L'opération contredit l'état existant (nom déjà pris, état incompatible) : 409."""

    code: ClassVar[str] = "CONFLICT"


# =============================================================================
# Lot B : ingestion
# =============================================================================


class FileTooLargeError(DomainError):
    """Fichier au-delà de MYPLAN_MAX_UPLOAD_BYTES (P0-03)."""

    code: ClassVar[str] = "FILE_TOO_LARGE"

    def __init__(self) -> None:
        super().__init__("Le fichier dépasse la taille maximale autorisée.")


class UnsupportedFileTypeError(DomainError):
    """Type hors liste blanche PDF / Markdown (P0-03)."""

    code: ClassVar[str] = "UNSUPPORTED_FILE_TYPE"

    def __init__(self, message: str = "Ce type de fichier n'est pas accepté.") -> None:
        super().__init__(message)


class ExtractionError(DomainError):
    """Échec d'extraction : le document passe en failed avec error_code (P0-04)."""

    code: ClassVar[str] = "EXTRACTION_FAILED"

    def __init__(self, error_code: str, message: str = "") -> None:
        """Crée l'erreur.

        Args:
            error_code: Valeur pour documents.error_code (EMPTY_TEXT, …).
            message: Explication affichable ; défaut = le code.
        """
        super().__init__(
            message or "L'extraction du document a échoué.",
            {"error_code": error_code},
        )
        self.error_code = error_code
