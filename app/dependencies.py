from pymongo.database import Database

from app.database import get_db
from app.repositories import SessionRepository, UserRepository
from app.services import AuthService, SessionService, UserService


db: Database = get_db()

user_repo = UserRepository(db)
session_repo = SessionRepository(db)

user_service = UserService(user_repo)
session_service = SessionService(session_repo=session_repo)

auth_service = AuthService(user_service=user_service)