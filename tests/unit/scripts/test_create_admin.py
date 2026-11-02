from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.errors.user import DuplicateEmailError
from scripts import create_admin


@pytest.fixture
def mocked_admin_dependencies(monkeypatch):
    db = object()

    repo = Mock()
    repo.create_admin.return_value = SimpleNamespace(
        email="admin@example.com",
    )

    init_db = Mock(return_value=db)
    ensure_all = Mock()
    close_db = Mock()
    repository_factory = Mock(return_value=repo)
    hash_password = Mock(return_value="hashed-password")

    monkeypatch.setattr(create_admin, "init_db", init_db)
    monkeypatch.setattr(create_admin, "ensure_all", ensure_all)
    monkeypatch.setattr(create_admin, "close_db", close_db)
    monkeypatch.setattr(
        create_admin,
        "UserRepository",
        repository_factory,
    )
    monkeypatch.setattr(
        create_admin,
        "hash_password",
        hash_password,
    )

    return {
        "db": db,
        "repo": repo,
        "init_db": init_db,
        "ensure_all": ensure_all,
        "close_db": close_db,
        "repository_factory": repository_factory,
        "hash_password": hash_password,
    }


def set_credentials(monkeypatch, email, password, confirmation):
    monkeypatch.setattr(
        "builtins.input",
        lambda _: email,
    )

    passwords = iter([password, confirmation])

    monkeypatch.setattr(
        create_admin,
        "getpass",
        lambda _: next(passwords),
    )


def test_create_admin_success(
    monkeypatch,
    mocked_admin_dependencies,
    capsys,
):
    set_credentials(
        monkeypatch,
        "ADMIN@EXAMPLE.COM",
        "securePassword123",
        "securePassword123",
    )

    create_admin.main()

    mocks = mocked_admin_dependencies

    mocks["init_db"].assert_called_once_with()
    mocks["ensure_all"].assert_called_once_with()

    mocks["repository_factory"].assert_called_once_with(
        mocks["db"],
    )

    mocks["hash_password"].assert_called_once_with(
        "securePassword123",
    )

    mocks["repo"].create_admin.assert_called_once_with(
        "admin@example.com",
        "hashed-password",
    )

    mocks["close_db"].assert_called_once_with()

    assert "Admin created: admin@example.com" in capsys.readouterr().out


def test_create_admin_password_mismatch(
    monkeypatch,
    mocked_admin_dependencies,
):
    set_credentials(
        monkeypatch,
        "admin@example.com",
        "securePassword123",
        "anotherPassword123",
    )

    with pytest.raises(SystemExit, match="Passwords do not match"):
        create_admin.main()

    mocked_admin_dependencies["init_db"].assert_not_called()


def test_create_admin_short_password(
    monkeypatch,
    mocked_admin_dependencies,
):
    set_credentials(
        monkeypatch,
        "admin@example.com",
        "short123",
        "short123",
    )

    with pytest.raises(
        SystemExit,
        match="Admin password must be at least 12 characters",
    ):
        create_admin.main()

    mocked_admin_dependencies["init_db"].assert_not_called()


def test_create_admin_invalid_email(
    monkeypatch,
    mocked_admin_dependencies,
    capsys,
):
    set_credentials(
        monkeypatch,
        "invalid-email",
        "securePassword123",
        "securePassword123",
    )

    with pytest.raises(SystemExit) as exc:
        create_admin.main()

    assert exc.value.code == 1
    assert "email" in capsys.readouterr().out

    mocked_admin_dependencies["init_db"].assert_not_called()


def test_create_admin_duplicate_email(
    monkeypatch,
    mocked_admin_dependencies,
):
    set_credentials(
        monkeypatch,
        "admin@example.com",
        "securePassword123",
        "securePassword123",
    )

    mocked_admin_dependencies["repo"].create_admin.side_effect = (
        DuplicateEmailError()
    )

    with pytest.raises(
        SystemExit,
        match="User with this email already exists",
    ):
        create_admin.main()

    mocked_admin_dependencies["close_db"].assert_called_once_with()


def test_create_admin_closes_database_on_error(
    monkeypatch,
    mocked_admin_dependencies,
):
    set_credentials(
        monkeypatch,
        "admin@example.com",
        "securePassword123",
        "securePassword123",
    )

    mocked_admin_dependencies["repo"].create_admin.side_effect = (
        RuntimeError("Database write failed")
    )

    with pytest.raises(RuntimeError, match="Database write failed"):
        create_admin.main()

    mocked_admin_dependencies["close_db"].assert_called_once_with()