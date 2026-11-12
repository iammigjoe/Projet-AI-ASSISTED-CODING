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
    TokenClaims,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    decrypt_secret,
    encrypt_secret,
    hash_password,
    verify_login_password,
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
    token = create_access_token(42, 0, NOW)

    assert decode_token(token, TokenType.ACCESS) == TokenClaims(user_id=42, token_version=0)


def test_refresh_token_is_refused_as_access_token():
    token = create_refresh_token(42, 0, NOW)

    with pytest.raises(InvalidTokenError):
        decode_token(token, TokenType.ACCESS)


def test_access_token_is_refused_as_refresh_token():
    token = create_access_token(42, 0, NOW)

    with pytest.raises(InvalidTokenError):
        decode_token(token, TokenType.REFRESH)


def test_expired_access_token_is_refused():
    token = create_access_token(42, 0, NOW - timedelta(hours=1))

    with pytest.raises(InvalidTokenError):
        decode_token(token, TokenType.ACCESS)


def test_token_signed_with_another_key_is_refused():
    forged = jwt.encode(
        {"sub": "42", "ver": 0, "type": "access", "iat": NOW, "exp": NOW + timedelta(minutes=5)},
        "another-secret-key-of-sufficient-length-000",
        algorithm="HS256",
    )

    with pytest.raises(InvalidTokenError):
        decode_token(forged, TokenType.ACCESS)


def test_unsigned_token_is_refused():
    unsigned = jwt.encode(
        {"sub": "42", "ver": 0, "type": "access", "iat": NOW, "exp": NOW + timedelta(minutes=5)},
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


def test_token_carries_token_version():
    token = create_access_token(42, 3, NOW)

    assert decode_token(token, TokenType.ACCESS).token_version == 3


def test_token_without_version_is_refused():
    legacy = jwt.encode(
        {"sub": "42", "type": "access", "iat": NOW, "exp": NOW + timedelta(minutes=5)},
        "test-secret-key-that-is-long-enough-0123456789",
        algorithm="HS256",
    )

    with pytest.raises(InvalidTokenError):
        decode_token(legacy, TokenType.ACCESS)


def test_login_password_for_unknown_account_is_false():
    assert not verify_login_password("any-password-123", None)


def test_login_password_for_known_account_checks_hash():
    password_hash = hash_password("correct horse battery staple")

    assert verify_login_password("correct horse battery staple", password_hash)
    assert not verify_login_password("wrong password", password_hash)
