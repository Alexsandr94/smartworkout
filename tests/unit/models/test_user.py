from datetime import UTC, datetime

from bson import ObjectId

from app.models.user import User
from app.models.auth import AuthTokens, LoginResult


def test_user_from_document():
    user_id = ObjectId()
    favorite_id = ObjectId()
    created_at = datetime.now(UTC)

    document = {
        "_id": user_id,
        "email": "admin@example.com",
        "password_hash": "hashed-password",
        "role": "ADMIN",
        "created_at": created_at,
        "favorite_program_ids": [favorite_id],
    }

    user = User.from_document(document)

    assert isinstance(user, User)
    assert user.id == user_id
    assert user.email == "admin@example.com"
    assert user.password_hash == "hashed-password"
    assert user.role == "ADMIN"
    assert user.created_at == created_at
    assert user.favorite_program_ids == [favorite_id]


def test_user_without_favorites():
    document = {
        "_id": ObjectId(),
        "email": "user@example.com",
        "password_hash": "hashed-password",
        "role": "USER",
        "created_at": datetime.now(UTC),
    }

    user = User.from_document(document)

    assert user.favorite_program_ids == []


def test_password_hash_not_in_repr():
    user = User(
        id=ObjectId(),
        email="admin@example.com",
        password_hash="very-secret-hash",
        role="ADMIN",
        created_at=datetime.now(UTC),
    )

    assert "very-secret-hash" not in repr(user)


def test_auth_models():
    user = User(
        id=ObjectId(),
        email="admin@example.com",
        password_hash="hashed",
        role="ADMIN",
        created_at=datetime.now(UTC),
    )

    tokens = AuthTokens(
        access_token="access-secret",
        refresh_token="refresh-secret",
        refresh_ttl=3600,
    )

    result = LoginResult(user=user, tokens=tokens)

    assert result.user is user
    assert result.tokens.access_token == "access-secret"
    assert result.tokens.refresh_token == "refresh-secret"
    assert result.tokens.refresh_ttl == 3600

    assert "access-secret" not in repr(tokens)
    assert "refresh-secret" not in repr(tokens)
    assert "refresh-secret" not in repr(result)