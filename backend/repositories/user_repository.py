"""
===============================================================================
Repository : UserRepository
===============================================================================
Objectif :
    Centraliser les requêtes sur les utilisateurs.

Responsabilités :
    - Ne jamais renvoyer un compte dont la suppression est demandée (deleted_at).
    - Chercher un compte par email en minuscules, comme il est stocké.
    - Créer un compte toujours avec ses paramètres d'étude par défaut.

Utilisé par :
    backend.api.deps (get_current_user), AuthService.

Exemple d'utilisation :
    user = UserRepository(session).get_active(user_id=42)

Lot :
    A (socle et sécurité)
===============================================================================
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db.models import User, UserSettings

# =============================================================================
# API publique
# =============================================================================


class UserRepository:
    """Accès aux comptes utilisateurs."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_active(self, user_id: int) -> User | None:
        """Récupère un compte actif par son identifiant.

        Args:
            user_id: Identifiant issu d'un jeton vérifié.

        Returns:
            Le compte, ou None s'il n'existe pas ou si sa suppression est demandée.
        """
        return self._session.scalar(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )

    def get_by_email(self, email: str) -> User | None:
        """Récupère un compte par email, sans tenir compte de la casse saisie."""
        return self._session.scalar(select(User).where(User.email == email.strip().lower()))

    def count(self) -> int:
        """Compte les utilisateurs, y compris ceux en cours de suppression.

        Sert à fermer l'inscription dès qu'un compte existe (modele_donnees.md §6.7).
        """
        return self._session.scalar(select(func.count()).select_from(User)) or 0

    def create(self, email: str, password_hash: str, timezone: str) -> User:
        """Crée un compte et ses paramètres d'étude par défaut.

        Un compte a toujours ses paramètres : les services n'ont jamais à
        tester leur absence. L'appelant valide la transaction.

        Args:
            email: Email déjà normalisé (minuscules).
            password_hash: Hachage argon2, jamais le mot de passe.
            timezone: Nom IANA du fuseau de l'étudiant.

        Returns:
            Le compte créé, avec son identifiant.
        """
        user = User(email=email, password_hash=password_hash, timezone=timezone)
        self._session.add(user)
        self._session.flush()
        self._session.add(UserSettings(user_id=user.id))
        self._session.flush()
        return user

    def revoke_tokens(self, user: User) -> None:
        """Révoque tous les jetons émis pour ce compte (déconnexion partout)."""
        user.token_version += 1
        self._session.flush()
