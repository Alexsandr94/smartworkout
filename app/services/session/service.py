from bson import ObjectId

from app.repositories.session import SessionRepository


class SessionService:
    def __init__(self, session_repo: SessionRepository):
        self.session_repo = session_repo

    def get_user_sessions(self, user_id: str) -> list[dict]:
        return self.session_repo.find_by_user_id(ObjectId(user_id))

