"""Password hashing and verification without external services."""

import pytest

from app.security.password import hash_password, verify_password


def test_password_hash_is_not_plaintext_and_verifies():
    password = "correct_password_123"
    stored = hash_password(password)
    assert stored != password
    assert stored.startswith("pbkdf2_sha256$")
    assert verify_password(password, stored)
    assert not verify_password("wrong_password_123", stored)


def test_hash_uses_a_new_salt_each_time():
    first = hash_password("same_password")
    second = hash_password("same_password")
    assert first != second
    assert verify_password("same_password", first)
    assert verify_password("same_password", second)


def test_password_is_case_and_whitespace_sensitive():
    stored = hash_password(" password ")
    assert verify_password(" password ", stored)
    assert not verify_password("password", stored)
    assert not verify_password(" Password ", stored)


@pytest.mark.parametrize("stored", [
    "", "not-a-hash", "unknown$600000$c2FsdA==$aGFzaA==",
    "pbkdf2_sha256$bad$abc$def", "pbkdf2_sha256$600000$%%%$%%%",
    None, 123,
])
def test_malformed_hash_is_rejected(stored):
    assert not verify_password("any_password", stored)


def test_invalid_password_types_are_rejected():
    assert not verify_password(None, hash_password("valid_password"))
    with pytest.raises(TypeError):
        hash_password(None)
