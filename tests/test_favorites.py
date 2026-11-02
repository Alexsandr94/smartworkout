import pytest
from bson import ObjectId
from unittest.mock import MagicMock

from app.services.favorite.service import FavoriteService
from app.errors.favorite import (
    InvalidProgramIdError,
    ProgramNotFoundError,
    AlreadyInFavoritesError,
    ProgramNotInFavoritesError,
    ForbiddenError,
)


# --- Фикстуры (подготовка данных) ---

@pytest.fixture
def mock_repo():
    """Создаем фейковый репозиторий"""
    return MagicMock()


@pytest.fixture
def service(mock_repo):
    """Создаем сервис с фейковым репозиторием"""
    return FavoriteService(mock_repo)


@pytest.fixture
def user_id():
    return str(ObjectId())


@pytest.fixture
def program_id():
    return str(ObjectId())


# --- Тесты для add_to_favorites ---

def test_add_to_favorites_success(service, mock_repo, user_id, program_id):
    mock_repo.get_program.return_value = {"author_id": str(ObjectId()), "is_public": True}
    mock_repo.add_to_favorites.return_value = True  # Атомарное обновление вернуло True

    service.add_to_favorites(user_id, program_id)

    mock_repo.add_to_favorites.assert_called_once()


def test_add_to_favorites_program_not_found(service, mock_repo, user_id, program_id):
    mock_repo.get_program.return_value = None  # Программа не найдена

    with pytest.raises(ProgramNotFoundError):
        service.add_to_favorites(user_id, program_id)


def test_add_to_favorites_own_program(service, mock_repo, user_id, program_id):
    mock_repo.get_program.return_value = {"author_id": user_id, "is_public": True}

    with pytest.raises(ForbiddenError):
        service.add_to_favorites(user_id, program_id)


def test_add_to_favorites_private_program(service, mock_repo, user_id, program_id):
    mock_repo.get_program.return_value = {"author_id": str(ObjectId()), "is_public": False}

    with pytest.raises(ProgramNotFoundError):
        service.add_to_favorites(user_id, program_id)


def test_add_to_favorites_already_exists(service, mock_repo, user_id, program_id):
    mock_repo.get_program.return_value = {"author_id": str(ObjectId()), "is_public": True}
    mock_repo.add_to_favorites.return_value = False  # Атомарное обновление вернуло False (не добавилось)

    with pytest.raises(AlreadyInFavoritesError):
        service.add_to_favorites(user_id, program_id)


# --- Тесты для remove_from_favorites ---

def test_remove_from_favorites_success(service, mock_repo, user_id, program_id):
    mock_repo.remove_from_favorites.return_value = True

    service.remove_from_favorites(user_id, program_id)

    mock_repo.remove_from_favorites.assert_called_once()


def test_remove_from_favorites_invalid_id(service, user_id):
    with pytest.raises(InvalidProgramIdError):
        service.remove_from_favorites(user_id, "not_a_valid_object_id")


def test_remove_from_favorites_not_in_list(service, mock_repo, user_id, program_id):
    mock_repo.remove_from_favorites.return_value = False

    with pytest.raises(ProgramNotInFavoritesError):
        service.remove_from_favorites(user_id, program_id)


# --- Тесты для get_favorites ---

def test_get_favorites_empty(service, mock_repo, user_id):
    mock_repo.get_favorite_ids.return_value = []
    result = service.get_favorites(user_id)
    assert result.data == []

def test_get_favorites_success(service, mock_repo, user_id):
    fake_program_id = ObjectId()
    mock_repo.get_favorite_ids.return_value = [fake_program_id]
    mock_repo.get_programs_by_ids.return_value = [{
        "_id": fake_program_id,
        "title": "Моя тренировка",
        "description": "Описание",
        "author_id": ObjectId(),
        "is_public": True,
        "difficulty": "Beginner"
    }]
    result = service.get_favorites(user_id)
    assert len(result.data) == 1
    assert result.data[0]["title"] == "Моя тренировка"