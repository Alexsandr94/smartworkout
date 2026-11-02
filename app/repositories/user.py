from datetime import UTC, datetime

from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.database.collections import USERS
from app.errors.user import DuplicateEmailError
from app.models.user import User, UserRole


class UserRepository:
    def __init__(self, db: Database):
        self.collection: Collection = db[USERS]

    def create(self, email: str, password_hash: str) -> User:
        return self._create(
            email=email,
            password_hash=password_hash,
            role="USER",
        )

    def create_admin(self, email: str, password_hash: str) -> User:
        return self._create(
            email=email,
            password_hash=password_hash,
            role="ADMIN",
        )

    def _create(
        self,
        email: str,
        password_hash: str,
        role: UserRole,
    ) -> User:
        document = {
            "email": email,
            "password_hash": password_hash,
            "role": role,
            "created_at": datetime.now(UTC),
            "favorite_program_ids": [],
        }

        try:
            result = self.collection.insert_one(document)
        except DuplicateKeyError:
            raise DuplicateEmailError() from None

        document["_id"] = result.inserted_id
        return User.from_document(document)

    def find_by_email(self, email: str) -> User | None:
        document = self.collection.find_one({"email": email})

        if document is None:
            return None

        return User.from_document(document)