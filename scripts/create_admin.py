from getpass import getpass

from app.database import init_db, close_db, ensure_all
from app.dtos.auth import RegisterDTO
from app.dtos.base import DTOValidationError
from app.errors.user import DuplicateEmailError
from app.repositories.user import UserRepository
from app.security.password import hash_password


MIN_ADMIN_PASSWORD_LENGTH = 12


def main() -> None:
    email = input("Admin email: ")
    password = getpass("Password: ")
    confirmation = getpass("Confirm password: ")

    if password != confirmation:
        raise SystemExit("Passwords do not match")

    try:
        dto = RegisterDTO.from_dict({
            "email": email,
            "password": password,
        })
    except DTOValidationError as exc:
        for error in exc.errors:
            print(f"{error['field']}: {error['message']}")

        raise SystemExit(1) from None

    if len(dto.password) < MIN_ADMIN_PASSWORD_LENGTH:
        raise SystemExit(
            f"Admin password must be at least "
            f"{MIN_ADMIN_PASSWORD_LENGTH} characters"
        )

    db = init_db()

    try:
        ensure_all()

        repo = UserRepository(db)

        try:
            user = repo.create_admin(
                dto.email,
                hash_password(dto.password),
            )
        except DuplicateEmailError:
            raise SystemExit(
                "User with this email already exists"
            ) from None

        print(f"Admin created: {user.email}")
    finally:
        close_db()


if __name__ == "__main__":
    main()