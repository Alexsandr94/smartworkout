from app.common.pagination import PaginationParams, paginate, Page
from bson import ObjectId

from app.errors.favorite import (
    InvalidProgramIdError,
    ProgramNotFoundError,
    AlreadyInFavoritesError,
    ProgramNotInFavoritesError,
    ForbiddenError,
)
from app.repositories.favorite import FavoriteRepository


class FavoriteService:
    def __init__(self, favorite_repo: FavoriteRepository):
        self.favorite_repo = favorite_repo

    def get_favorites(self, user_id: str, limit: int = 20, cursor: ObjectId | None = None) -> Page[dict]:
        user_obj_id = ObjectId(user_id)
        favorite_ids = self.favorite_repo.get_favorite_ids(user_obj_id)

        if not favorite_ids:
            return Page(data=[], next=None, limit=limit, has_more=False)

        programs = self.favorite_repo.get_programs_by_ids(favorite_ids, limit + 1, cursor)

        params = PaginationParams(limit=limit, cursor=cursor)

        page = paginate(programs, params, key=lambda p: p["_id"])

        page.data = [self._to_short_view(p) for p in page.data]

        return page

    def add_to_favorites(self, user_id: str, program_id: str) -> None:
        user_obj_id = ObjectId(user_id)
        program_obj_id = ObjectId(program_id)

        program = self.favorite_repo.get_program(program_obj_id)
        if not program:
            raise ProgramNotFoundError()

        author_id = program.get("author_id")
        is_own = author_id is not None and ObjectId(author_id) == user_obj_id

        if is_own:
            raise ForbiddenError()
        if not program.get("is_public"):
            raise ProgramNotFoundError()

        added = self.favorite_repo.add_to_favorites(user_obj_id, program_obj_id)
        if not added:
            raise AlreadyInFavoritesError()

    def remove_from_favorites(self, user_id: str, program_id: str) -> None:
        if not ObjectId.is_valid(program_id):
            raise InvalidProgramIdError()

        user_obj_id = ObjectId(user_id)
        program_obj_id = ObjectId(program_id)

        removed = self.favorite_repo.remove_from_favorites(user_obj_id, program_obj_id)

        if not removed:
            raise ProgramNotInFavoritesError()

    @staticmethod
    def _to_short_view(program: dict) -> dict:
        return {
            "id": str(program["_id"]),
            "title": program.get("title", ""),
            "description": program.get("description", ""),
            "author_id": str(program["author_id"]) if program.get("author_id") else None,
            "is_public": program.get("is_public", False),
            "difficulty": program.get("difficulty"),
        }