"""Argon2id password hasher (AUTH-07), implementing the PasswordHasher port."""

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError


class Argon2PasswordHasher:
    def __init__(self) -> None:
        self._hasher = PasswordHasher(type=Type.ID)

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (VerificationError, InvalidHashError):
            return False
