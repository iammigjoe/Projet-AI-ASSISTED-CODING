"""
===============================================================================
Service : AuthService
===============================================================================
Objectif :
    Inscription, connexion, renouvellement des jetons et déconnexion (P0-01).

Responsabilités :
    - Un seul compte au départ : l'inscription est fermée dès qu'un compte
      existe (modele_donnees.md §6.7).
    - Appliquer la politique de mots de passe à l'inscription.
    - Freiner la force brute à la connexion : attente exponentielle par email
      et par IP, réponse identique et de même durée que l'email existe ou non
      (docs/securite.md §3).
    - Déconnecter en révoquant tous les jetons du compte.

Dépendances :
    Session SQLAlchemy, Clock, LoginThrottle

Utilisé par :
    backend/api/routers/auth.py

Lève :
    RegistrationClosedError    inscription alors qu'un compte existe
    WeakPasswordError          mot de passe refusé par la politique
    InvalidCredentialsError    email ou mot de passe incorrect, jeton de rafraîchissement refusé
    TooManyLoginAttemptsError  trop d'échecs récents pour cet email ou cette IP

Exemple d'utilisation :
    tokens = AuthService(session, clock, throttle).login(email, password, client_ip)

Lot :
    A (socle et sécurité)
===============================================================================
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.core.clock import Clock
from backend.core.config import get_settings
from backend.core.login_throttle import LoginThrottle
from backend.core.security import (
    InvalidTokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_login_password,
)
from backend.db.models import User
from backend.domain.errors import (
    InvalidCredentialsError,
    RegistrationClosedError,
    TooManyLoginAttemptsError,
    WeakPasswordError,
)
from backend.domain.password_policy import password_problems
from backend.repositories.user_repository import UserRepository

# =============================================================================
# Constantes
# =============================================================================

INVALID_CREDENTIALS_MESSAGE = "Email ou mot de passe incorrect."

# =============================================================================
# Types
# =============================================================================


@dataclass(frozen=True)
class AuthTokens:
    """Paire de jetons émise pour un compte."""

    access_token: str
    refresh_token: str
    expires_in: int


# =============================================================================
# API publique
# =============================================================================


class AuthService:
    """Cas d'usage de l'authentification."""

    def __init__(self, session: Session, clock: Clock, throttle: LoginThrottle) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._clock = clock
        self._throttle = throttle

    def register(self, email: str, password: str, timezone: str) -> AuthTokens:
        """Crée le compte unique et renvoie ses premiers jetons.

        Args:
            email: Email normalisé (schéma EmailAddress).
            password: Mot de passe saisi.
            timezone: Nom IANA déjà vérifié.

        Returns:
            Les jetons du nouveau compte : l'étudiant est connecté.

        Raises:
            RegistrationClosedError: Si un compte existe déjà.
            WeakPasswordError: Si le mot de passe est refusé ; details["problems"]
                liste les raisons.
        """
        if self._users.count() > 0:
            raise RegistrationClosedError("Un compte existe déjà : l'inscription est fermée.")

        problems = password_problems(password, email=email)
        if problems:
            raise WeakPasswordError("Mot de passe trop faible.", {"problems": problems})

        user = self._users.create(email, hash_password(password), timezone)
        self._session.commit()
        return self._issue_tokens(user)

    def login(self, email: str, password: str, client_ip: str) -> AuthTokens:
        """Vérifie les identifiants et renvoie une paire de jetons.

        Args:
            email: Email normalisé.
            password: Mot de passe saisi.
            client_ip: Adresse d'origine, pour freiner une IP qui essaie beaucoup.

        Raises:
            TooManyLoginAttemptsError: Si l'email ou l'IP doit encore attendre.
            InvalidCredentialsError: Si l'email est inconnu ou le mot de passe
                faux ; le message ne dit pas lequel des deux.
        """
        now = self._clock()
        keys = (f"email:{email}", f"ip:{client_ip}")

        wait = self._throttle.retry_after(keys, now)
        if wait > 0:
            raise TooManyLoginAttemptsError(wait)

        user = self._users.get_by_email(email)
        active_user = user if user is not None and user.deleted_at is None else None
        password_hash = active_user.password_hash if active_user else None

        if active_user is None or not verify_login_password(password, password_hash):
            self._throttle.record_failure(keys, now)
            raise InvalidCredentialsError(INVALID_CREDENTIALS_MESSAGE)

        self._throttle.record_success(keys)
        return self._issue_tokens(active_user)

    def refresh(self, refresh_token: str) -> AuthTokens:
        """Échange un jeton de rafraîchissement valide contre une nouvelle paire.

        Raises:
            InvalidCredentialsError: Si le jeton est invalide, expiré, révoqué,
                ou si le compte n'existe plus.
        """
        try:
            claims = decode_token(refresh_token, TokenType.REFRESH)
        except InvalidTokenError:
            raise InvalidCredentialsError("Session expirée. Reconnectez-vous.") from None

        user = self._users.get_active(claims.user_id)
        if user is None or user.token_version != claims.token_version:
            raise InvalidCredentialsError("Session expirée. Reconnectez-vous.")
        return self._issue_tokens(user)

    def logout(self, user: User) -> None:
        """Déconnecte le compte partout en révoquant tous ses jetons."""
        self._users.revoke_tokens(user)
        self._session.commit()

    # --- Fonctions internes -------------------------------------------------

    def _issue_tokens(self, user: User) -> AuthTokens:
        now = self._clock()
        return AuthTokens(
            access_token=create_access_token(user.id, user.token_version, now),
            refresh_token=create_refresh_token(user.id, user.token_version, now),
            expires_in=get_settings().jwt_access_ttl_min * 60,
        )
