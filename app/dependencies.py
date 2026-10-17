from app.repositories import ExerciseRepository, UserRepository
from app.services import ExerciseService, UserService, AuthService
from app.database import get_db

from pymongo.database import Database

db: Database = get_db()

exercise_repo = ExerciseRepository(db)
exercise_service = ExerciseService(exercise_repo)

user_repo = UserRepository(db)
user_service = UserService(user_repo)
auth_service = AuthService(
    user_service=user_service,
)
