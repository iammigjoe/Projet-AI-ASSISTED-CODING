"""
===============================================================================
Module : security
===============================================================================
Objectif :
    Primitives de sécurité : hachage des mots de passe, jetons JWT, chiffrement
    des secrets stockés en base.

Responsabilités :
    - Hacher les mots de passe avec argon2 ; ne jamais les comparer en clair.
    - Prendre le même temps qu'un compte existe ou non (verify_login_password),
      pour qu'on ne puisse pas deviner les emails inscrits en chronométrant.
    - Signer et vérifier les jetons d'accès (courts) et de rafraîchissement ;
      un jeton d'un type n'est jamais accepté pour l'autre.
    - Inscrire dans chaque jeton la version de jeton du compte : l'incrémenter
      révoque d'un coup tous les jetons émis (déconnexion, mot de passe changé).
    - Chiffrer et déchiffrer avec Fernet (refresh token Google, lot D).

Utilisé par :
    backend.api.deps (get_current_user), AuthService, le lot D pour les
    identifiants Google.

Lève :
    InvalidTokenError  si un jeton est absent, expiré, mal signé ou du mauvais type

Exemple d'utilisation :
    token = create_access_token(user.id, user.token_version, now=clock())
    claims = decode_token(token, TokenType.ACCESS)

Lot :
    A (socle et sécurité)
===============================================================================
"""

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from functools import cache

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from cryptography.fernet import Fernet

from backend.core.config import get_settings

# =============================================================================
# Constantes
# =============================================================================

JWT_ALGORITHM = "HS256"

_password_hasher = PasswordHasher()

# =============================================================================
# Types
# =============================================================================


class TokenType(StrEnum):
    """Nature d'un jeton, inscrite dans le jeton lui-même (claim « type »)."""

    ACCESS = "access"
    REFRESH = "refresh"


@dataclass(frozen=True)
class TokenClaims:
    """Contenu vérifié d'un jeton."""

    user_id: int
    token_version: int


class InvalidTokenError(Exception):
    """Jeton refusé, quelle qu'en soit la raison (la raison n'est pas exposée)."""


# =============================================================================
# API publique
# =============================================================================


def hash_password(password: str) -> str:
    """Hache un mot de passe avec argon2 (sel aléatoire inclus dans le résultat)."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Vérifie un mot de passe contre son hachage.

    Returns:
        True si le mot de passe correspond ; False sinon, y compris si le
        hachage stocké est illisible.
    """
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def verify_login_password(password: str, password_hash: str | None) -> bool:
    """Vérifie un mot de passe de connexion, que le compte existe ou non.

    Sans compte, un hachage factice est quand même vérifié : la réponse prend
    le même temps, et un attaquant ne peut pas distinguer « email inconnu »
    de « mauvais mot de passe » en chronométrant.

    Args:
        password: Mot de passe saisi.
        password_hash: Hachage du compte, ou None si l'email est inconnu.

    Returns:
        True seulement si le compte existe et que le mot de passe correspond.
    """
    if password_hash is None:
        verify_password(password, _dummy_hash())
        return False
    return verify_password(password, password_hash)


def create_access_token(user_id: int, token_version: int, now: datetime) -> str:
    """Crée un jeton d'accès, valable MYPLAN_JWT_ACCESS_TTL_MIN minutes.

    Args:
        user_id: Utilisateur authentifié.
        token_version: Version de jeton actuelle du compte (users.token_version).
        now: Instant de création, avec fuseau (horloge injectée).
    """
    ttl = timedelta(minutes=get_settings().jwt_access_ttl_min)
    return _create_token(user_id, token_version, TokenType.ACCESS, now, ttl)


def create_refresh_token(user_id: int, token_version: int, now: datetime) -> str:
    """Crée un jeton de rafraîchissement, valable MYPLAN_JWT_REFRESH_TTL_DAYS jours."""
    ttl = timedelta(days=get_settings().jwt_refresh_ttl_days)
    return _create_token(user_id, token_version, TokenType.REFRESH, now, ttl)


def decode_token(token: str, expected_type: TokenType) -> TokenClaims:
    """Vérifie un jeton et renvoie ce qu'il contient.

    L'appelant doit encore comparer token_version à celle du compte : un jeton
    d'une version antérieure a été révoqué.

    Args:
        token: Jeton reçu du client.
        expected_type: Type attendu ; un jeton de rafraîchissement n'ouvre
            jamais l'accès à l'API, et inversement.

    Returns:
        L'utilisateur et la version de jeton inscrits dans le jeton.

    Raises:
        InvalidTokenError: Si le jeton est expiré, mal signé, mal formé ou
            d'un autre type.
    """
    try:
        claims = jwt.decode(
            token,
            get_settings().jwt_secret_key.get_secret_value(),
            # Liste fermée : « none » et les algorithmes asymétriques sont refusés.
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub", "type", "ver"]},
        )
    except jwt.PyJWTError as error:
        raise InvalidTokenError from error

    if claims["type"] != expected_type:
        raise InvalidTokenError
    try:
        return TokenClaims(user_id=int(claims["sub"]), token_version=int(claims["ver"]))
    except (TypeError, ValueError) as error:
        raise InvalidTokenError from error


def encrypt_secret(plaintext: str) -> bytes:
    """Chiffre un secret avant de le stocker en base (Fernet, MYPLAN_FERNET_KEY)."""
    return _fernet().encrypt(plaintext.encode())


def decrypt_secret(ciphertext: bytes) -> str:
    """Déchiffre un secret stocké par encrypt_secret.

    Raises:
        cryptography.fernet.InvalidToken: Si la donnée a été modifiée ou chiffrée
            avec une autre clé.
    """
    return _fernet().decrypt(ciphertext).decode()


# =============================================================================
# Fonctions internes
# =============================================================================


def _create_token(
    user_id: int, token_version: int, token_type: TokenType, now: datetime, ttl: timedelta
) -> str:
    claims = {
        "sub": str(user_id),
        "ver": token_version,
        "type": token_type.value,
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(
        claims, get_settings().jwt_secret_key.get_secret_value(), algorithm=JWT_ALGORITHM
    )


@cache
def _dummy_hash() -> str:
    """Hachage d'un secret aléatoire jamais conservé, calculé une seule fois."""
    return _password_hasher.hash(secrets.token_urlsafe(32))


def _fernet() -> Fernet:
    return Fernet(get_settings().fernet_key.get_secret_value())
