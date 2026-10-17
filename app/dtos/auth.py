import re
from dataclasses import dataclass

from app.dtos.base import BaseDTO

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

MIN_PASSWORD_LENGTH = 6
MAX_PASSWORD_LENGTH = 32

@dataclass
class RegisterDTO(BaseDTO):
    email: str
    password: str

    no_strip_fields = frozenset({"password"})

    def _validate_email(self, value: str) -> str | None:
        self.email = value.lower()
        if not EMAIL_RE.match(self.email):
            return "invalid email address"
        return None

    def _validate_password(self, value: str) -> str | None:
        if len(value) < MIN_PASSWORD_LENGTH:
            return f"password must be at least {MIN_PASSWORD_LENGTH} characters long"

        if len(value) > MAX_PASSWORD_LENGTH:
            return f"password must be at most {MAX_PASSWORD_LENGTH} characters long"
        return None

@dataclass
class LoginDTO(BaseDTO):
    email: str
    password: str

    no_strip_fields = frozenset({"password"})

    def _validate_email(self, value: str) -> str | None:
        if not value or not value.strip():
            return "email is required"

        self.email = value.strip().lower()
        return None

    def _validate_password(self, value: str) -> str | None:
        if not value:
            return "password is required"
        return None