from unittest.mock import Mock

import pytest

from app.errors.user import DuplicateEmailError
from app.models.auth import LoginResult
from app.models.user import User
from app.repositories.user import UserRepository
from app.security.password import hash_password, verify_password
from app.security.token import verify
from app.core.config import settings
from app.services.auth.service import AuthService
from app.services.user.service import UserService
from scripts import create_admin


@pytest.fixture
def user_repo(exercise_repo):
    db = exercise_repo.collection.database
    return UserRepository(db)


def test_create_admin(user_repo):
    password = "securePassword123"
    password_hash = hash_password(password)

    admin = user_repo.create_admin(
        "admin@example.com",
        password_hash,
    )

    assert isinstance(admin, User)
    assert admin.email == "admin@example.com"
    assert admin.role == "ADMIN"
    assert admin.password_hash != password
    assert verify_password(password, admin.password_hash)
    assert admin.favorite_program_ids == []

    stored = user_repo.collection.find_one({
        "_id": admin.id,
    })

    assert stored is not None
    assert stored["role"] == "ADMIN"
    assert stored["password_hash"] == password_hash


def test_create_regular_user(user_repo):
    user = user_repo.create(
        "user@example.com",
        hash_password("securePassword123"),
    )

    assert isinstance(user, User)
    assert user.role == "USER"

    stored = user_repo.collection.find_one({
        "_id": user.id,
    })

    assert stored["role"] == "USER"


def test_find_admin_by_email(user_repo):
    created = user_repo.create_admin(
        "admin@example.com",
        hash_password("securePassword123"),
    )

    found = user_repo.find_by_email("admin@example.com")

    assert isinstance(found, User)
    assert found.id == created.id
    assert found.role == "ADMIN"


def test_duplicate_admin_email(user_repo):
    password_hash = hash_password("securePassword123")

    user_repo.create_admin(
        "admin@example.com",
        password_hash,
    )

    with pytest.raises(DuplicateEmailError):
        user_repo.create_admin(
            "admin@example.com",
            password_hash,
        )

    assert user_repo.collection.count_documents({
        "email": "admin@example.com",
    }) == 1


def test_admin_can_login(user_repo):
    password = "securePassword123"

    admin = user_repo.create_admin(
        "admin@example.com",
        hash_password(password),
    )

    user_service = UserService(user_repo)
    auth_service = AuthService(user_service)

    result = auth_service.login(
        "admin@example.com",
        password,
    )

    assert isinstance(result, LoginResult)
    assert isinstance(result.user, User)
    assert result.user.id == admin.id
    assert result.user.role == "ADMIN"

    payload = verify(
        result.tokens.access_token,
        settings.token_secret,
        "access",
    )

    assert payload["sub"] == str(admin.id)
    assert payload["role"] == "ADMIN"


def test_create_admin_script_with_database(
    user_repo,
    monkeypatch,
    capsys,
):
    db = user_repo.collection.database

    monkeypatch.setattr(
        create_admin,
        "init_db",
        lambda: db,
    )

    # Индексы и валидаторы уже созданы фикстурой.
    monkeypatch.setattr(
        create_admin,
        "ensure_all",
        lambda: None,
    )

    close_db = Mock()

    monkeypatch.setattr(
        create_admin,
        "close_db",
        close_db,
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "admin@example.com",
    )

    monkeypatch.setattr(
        create_admin,
        "getpass",
        lambda _: "securePassword123",
    )

    create_admin.main()

    admin = user_repo.find_by_email("admin@example.com")

    assert admin is not None
    assert admin.role == "ADMIN"
    assert verify_password(
        "securePassword123",
        admin.password_hash,
    )

    close_db.assert_called_once_with()

    assert "Admin created" in capsys.readouterr().out