"""AUTH-07 and AD-003: Argon2id hashing and session tokens."""

import hashlib

from app.infrastructure.security.argon2_hasher import Argon2PasswordHasher
from app.infrastructure.security.tokens import hash_token, new_csrf_token, new_session_token

PASSWORD = "senha-forte-123"


def test_hash_is_argon2id_and_never_contains_password():
    password_hash = Argon2PasswordHasher().hash(PASSWORD)

    assert password_hash.startswith("$argon2id$")
    assert PASSWORD not in password_hash


def test_verify_accepts_correct_password():
    hasher = Argon2PasswordHasher()
    assert hasher.verify(hasher.hash(PASSWORD), PASSWORD) is True


def test_verify_rejects_wrong_password():
    hasher = Argon2PasswordHasher()
    assert hasher.verify(hasher.hash(PASSWORD), "senha-errada-123") is False


def test_verify_rejects_malformed_hash():
    assert Argon2PasswordHasher().verify("not-a-hash", PASSWORD) is False


def test_session_tokens_are_random_and_long():
    tokens = {new_session_token() for _ in range(50)}
    assert len(tokens) == 50
    assert all(len(t) >= 43 for t in tokens)  # 32 random bytes, url-safe base64


def test_csrf_tokens_are_random_and_long():
    tokens = {new_csrf_token() for _ in range(50)}
    assert len(tokens) == 50
    assert all(len(t) >= 43 for t in tokens)


def test_hash_token_is_sha256_hex():
    token = new_session_token()
    digest = hash_token(token)

    assert digest == hashlib.sha256(token.encode()).hexdigest()
    assert len(digest) == 64
    assert token not in digest
