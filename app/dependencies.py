from pymongo.database import Database

from app.database import get_db
from app.repositories import (
    ExerciseRepository,
    ProgramRepository,
    SessionRepository,
    UserRepository,
)
from app.repositories.favorite import FavoriteRepository
from app.services import (
    AuthService,
    ExerciseService,
    ProgramService,
    SessionService,
    UserService,
)
from app.services.favorite.service import FavoriteService


db: Database = get_db()

exercise_repo = ExerciseRepository(db)
user_repo = UserRepository(db)
session_repo = SessionRepository(db)
favorite_repo = FavoriteRepository(db)
program_repo = ProgramRepository(db)

exercise_service = ExerciseService(exercise_repo)
user_service = UserService(user_repo)
session_service = SessionService(session_repo=session_repo)
favorite_service = FavoriteService(favorite_repo)
program_service = ProgramService(program_repo)

auth_service = AuthService(
    user_service=user_service,
)