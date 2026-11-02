from dataclasses import dataclass

from app.dtos.base import BaseDTO, DTOValidationError
from app.dtos.utils import validate_object_id


@dataclass
class FavoriteDTO(BaseDTO):
    program_id: str

    def _validate_program_id(self, value: str) -> str | None:
        try:
            validate_object_id(value, "program_id")
        except DTOValidationError:
            return "invalid program id format"
        return None