
from dataclasses import MISSING, fields
from typing import ClassVar, get_args, get_origin, get_type_hints


class DTOValidationError(Exception):
    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        super().__init__(f"{len(errors)} validation error(s)")


class BaseDTO:
    no_strip_fields: ClassVar[frozenset[str]] = frozenset()

    @classmethod
    def from_dict(cls, data: object):
        if not isinstance(data, dict):
            raise DTOValidationError([
                {"field": "body", "message": "body must be an object"}
            ])

        dto_fields = {field.name: field for field in fields(cls)}
        errors = []

        for field in dto_fields.values():
            required = (
                field.default is MISSING
                and field.default_factory is MISSING
            )

            if field.name not in data and required:
                errors.append({
                    "field": field.name,
                    "message": f"{field.name} is required",
                })
            elif field.name in data and data[field.name] is None:
                errors.append({
                    "field": field.name,
                    "message": f"{field.name} cannot be null",
                })

        for name in data:
            if name not in dto_fields:
                errors.append({
                    "field": name,
                    "message": f"{name} is not allowed",
                })

        if errors:
            raise DTOValidationError(errors)

        return cls(**data)

    def __post_init__(self):
        errors = []
        hints = get_type_hints(type(self))

        for field in fields(self):
            name = field.name
            value = getattr(self, name)

            required = (
                field.default is MISSING
                and field.default_factory is MISSING
            )

            if value is None:
                if required:
                    errors.append({
                        "field": name,
                        "message": f"{name} is required",
                    })
                continue

            annotation = hints[name]
            args = get_args(annotation)

            if type(None) in args:
                annotation = next(
                    arg for arg in args
                    if arg is not type(None)
                )

            expected = get_origin(annotation) or annotation

            if isinstance(expected, type) and type(value) is not expected:
                errors.append({
                    "field": name,
                    "message": f"{name} must be {expected.__name__}",
                })
                continue

            if isinstance(value, str):
                if name not in self.no_strip_fields:
                    value = value.strip()
                    setattr(self, name, value)

                if required and not value.strip():
                    errors.append({
                        "field": name,
                        "message": f"{name} cannot be blank",
                    })
                    continue

            validator = getattr(self, f"_validate_{name}", None)

            if validator is not None:
                message = validator(value)

                if message is not None:
                    errors.append({
                        "field": name,
                        "message": message,
                    })

        if errors:
            raise DTOValidationError(errors)