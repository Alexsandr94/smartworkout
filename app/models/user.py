from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from bson import ObjectId


UserRole = Literal["USER", "ADMIN"]


@dataclass
class User:
    id: ObjectId
    email: str
    password_hash: str = field(repr=False)
    role: UserRole
    created_at: datetime
    favorite_program_ids: list[ObjectId] = field(default_factory=list)

    @classmethod
    def from_document(cls, document: dict) -> "User":
        return cls(
            id=document["_id"],
            email=document["email"],
            password_hash=document["password_hash"],
            role=document["role"],
            created_at=document["created_at"],
            favorite_program_ids=list(
                document.get("favorite_program_ids", [])
            ),
        )