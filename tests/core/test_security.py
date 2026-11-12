"""
===============================================================================
Tests : security
===============================================================================
Objectif :
    Vérifier le hachage des mots de passe, les jetons JWT (expiration, type,
    signature) et le chiffrement Fernet.

Lot :
    A (socle et sécurité)
===============================================================================
"""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.fernet import InvalidToken

from backend.core.security import (
    InvalidTokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    decrypt_secret,
    encrypt_secret,
    hash_password,
    verify_password,
)

NOW = datetime.now(UTC)


def test_password_hash_verifies_and_is_not_plaintext():
    password_hash = hash_password("correct horse battery staple")

    assert "correct horse" not in password_hash
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong password", password_hash)


def test_same_password_gives_different_hashes():
    assert hash_password("secret-123") != hash_password("secret-123")


def test_verify_password_with_corrupted_hash_returns_false():
    assert not verify_password("secret-123", "not-an-argon2-hash")


def test_access_token_round_trips_user_id():
    token = create_access_token(42, NOW)

    assert decode_token(token, TokenType.ACCESS) == 42


def test_refresh_token_is_refused_as_access_token():
    token = create_refresh_token(42, NOW)

    with pytest.raises(InvalidTokenError):
        decode_token(token, TokenType.ACCESS)


def test_access_token_is_refused_as_refresh_token():
    token = create_access_token(42, NOW)

    with pytest.raises(InvalidTokenError):
        decode_token(token, TokenType.REFRESH)


def test_expired_access_token_is_refused():
    token = create_access_token(42, NOW - timedelta(hours=1))

    with pytest.raises(InvalidTokenError):
        decode_token(token, TokenType.ACCESS)


def test_token_signed_with_another_key_is_refused():
    forged = jwt.encode(
        {"sub": "42", "type": "access", "iat": NOW, "exp": NOW + timedelta(minutes=5)},
        "another-secret-key-of-sufficient-length-000",
        algorithm="HS256",
    )

    with pytest.raises(InvalidTokenError):
        decode_token(forged, TokenType.ACCESS)


def test_unsigned_token_is_refused():
    unsigned = jwt.encode(
        {"sub": "42", "type": "access", "iat": NOW, "exp": NOW + timedelta(minutes=5)},
        key=None,
        algorithm="none",
    )

    with pytest.raises(InvalidTokenError):
        decode_token(unsigned, TokenType.ACCESS)


def test_garbage_token_is_refused():
    with pytest.raises(InvalidTokenError):
        decode_token("not.a.token", TokenType.ACCESS)


def test_encrypted_secret_round_trips_and_hides_plaintext():
    ciphertext = encrypt_secret("google-refresh-token")

    assert b"google-refresh-token" not in ciphertext
    assert decrypt_secret(ciphertext) == "google-refresh-token"


def test_tampered_ciphertext_is_refused():
    ciphertext = bytearray(encrypt_secret("google-refresh-token"))
    ciphertext[-5] ^= 1

    with pytest.raises(InvalidToken):
        decrypt_secret(bytes(ciphertext))
