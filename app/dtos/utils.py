from bson import ObjectId
from bson.errors import InvalidId

from app.dtos.base import DTOValidationError

def validate_object_id(value: object, field: str = 'id') -> ObjectId:
    if isinstance(value, str):
        try:
            return ObjectId(value)
        except InvalidId:
            pass
    raise DTOValidationError([{'field': field, 'message': f'{field} is invalid'}])