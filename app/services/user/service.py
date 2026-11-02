from app.models.user import User
from app.repositories.user import UserRepository


class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def create(self, email: str, password_hash: str) -> User:
        return self.user_repo.create(email, password_hash)

    def find_by_email(self, email: str) -> User | None:
        return self.user_repo.find_by_email(email)