"""
===============================================================================
Module : security
===============================================================================
Objectif :
    Primitives de sécurité : hachage des mots de passe, jetons JWT, chiffrement
    des secrets stockés en base.

Responsabilités :
    - Hacher les mots de passe avec argon2 ; ne jamais les comparer en clair.
    - Signer et vérifier les jetons d'accès (courts) et de rafraîchissement ;
      un jeton d'un type n'est jamais accepté pour l'autre.
    - Chiffrer et déchiffrer avec Fernet (refresh token Google, lot D).

Utilisé par :
    backend.api.deps (get_current_user), AuthService, le lot D pour les
    identifiants Google.

Lève :
    InvalidTokenError  si un jeton est absent, expiré, mal signé ou du mauvais type

Exemple d'utilisation :
    token = create_access_token(user_id=user.id, now=clock())
    user_id = decode_token(token, TokenType.ACCESS)

Lot :
    A (socle et sécurité)
===============================================================================
"""

from datetime import datetime, timedelta
from enum import StrEnum

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


class InvalidTokenError(Exception):
    """Jeton refusé, quelle qu'en soit la raison (la raison n'est pas exposée)."""


# =============================================================================
# API publique
# =============================================================================


def hash_password(password: str) -> str:
    """Hache un mot de passe avec argon2 (sel aléatoire inclus dans le résultat)."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Vérifie un mot de passe contre son hachage, en temps constant.

    Returns:
        True si le mot de passe correspond ; False sinon, y compris si le
        hachage stocké est illisible.
    """
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: int, now: datetime) -> str:
    """Crée un jeton d'accès, valable MYPLAN_JWT_ACCESS_TTL_MIN minutes.

    Args:
        user_id: Utilisateur authentifié.
        now: Instant de création, avec fuseau (horloge injectée).
    """
    ttl = timedelta(minutes=get_settings().jwt_access_ttl_min)
    return _create_token(user_id, TokenType.ACCESS, now, ttl)


def create_refresh_token(user_id: int, now: datetime) -> str:
    """Crée un jeton de rafraîchissement, valable MYPLAN_JWT_REFRESH_TTL_DAYS jours."""
    ttl = timedelta(days=get_settings().jwt_refresh_ttl_days)
    return _create_token(user_id, TokenType.REFRESH, now, ttl)


def decode_token(token: str, expected_type: TokenType) -> int:
    """Vérifie un jeton et renvoie l'utilisateur qu'il désigne.

    Args:
        token: Jeton reçu du client.
        expected_type: Type attendu ; un jeton de rafraîchissement n'ouvre
            jamais l'accès à l'API, et inversement.

    Returns:
        L'identifiant de l'utilisateur.

    Raises:
        InvalidTokenError: Si le jeton est expiré, mal signé, mal formé ou
            d'un autre type.
    """
    try:
        claims = jwt.decode(
            token,
            get_settings().jwt_secret_key.get_secret_value(),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub", "type"]},
        )
    except jwt.PyJWTError as error:
        raise InvalidTokenError from error

    if claims["type"] != expected_type:
        raise InvalidTokenError
    try:
        return int(claims["sub"])
    except ValueError as error:
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


def _create_token(user_id: int, token_type: TokenType, now: datetime, ttl: timedelta) -> str:
    claims = {"sub": str(user_id), "type": token_type.value, "iat": now, "exp": now + ttl}
    return jwt.encode(
        claims, get_settings().jwt_secret_key.get_secret_value(), algorithm=JWT_ALGORITHM
    )


def _fernet() -> Fernet:
    return Fernet(get_settings().fernet_key.get_secret_value())
