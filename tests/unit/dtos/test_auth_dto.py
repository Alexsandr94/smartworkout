"""Validation of auth request DTOs."""

import pytest

from app.dtos.auth import LoginDTO, RegisterDTO
from app.dtos.base import DTOValidationError


EMAIL = "student@example.test"
PASSWORD = "secure_password"


def assert_invalid(dto_class, payload, expected_field):
    with pytest.raises(DTOValidationError) as caught:
        dto_class.from_dict(payload)
    assert expected_field in {error["field"] for error in caught.value.errors}


def test_register_normalizes_email_and_preserves_password():
    dto = RegisterDTO.from_dict({
        "email": "  Student@EXAMPLE.TEST  ",
        "password": "  secure_password  ",
    })
    assert dto.email == EMAIL
    assert dto.password == "  secure_password  "


@pytest.mark.parametrize("payload,field", [
    ({}, "email"),
    ({"email": EMAIL}, "password"),
    ({"password": PASSWORD}, "email"),
    ({"email": None, "password": PASSWORD}, "email"),
    ({"email": EMAIL, "password": None}, "password"),
    ({"email": EMAIL, "password": PASSWORD, "role": "ADMIN"}, "role"),
    ({"email": 123, "password": PASSWORD}, "email"),
    ({"email": EMAIL, "password": 123}, "password"),
])
def test_register_rejects_invalid_structure(payload, field):
    assert_invalid(RegisterDTO, payload, field)


@pytest.mark.parametrize("email", ["", "  ", "not-an-email", "user@", "@example.test", "name@example"])
def test_register_rejects_invalid_email(email):
    assert_invalid(RegisterDTO, {"email": email, "password": PASSWORD}, "email")


def test_register_password_length_boundaries():
    for length in (6, 32):
        dto = RegisterDTO.from_dict({"email": EMAIL, "password": "x" * length})
        assert len(dto.password) == length
    for length in (5, 33):
        assert_invalid(RegisterDTO, {"email": EMAIL, "password": "x" * length}, "password")


@pytest.mark.parametrize("payload", [None, [], "hello", True, 42])
def test_register_requires_json_object(payload):
    assert_invalid(RegisterDTO, payload, "body")

@pytest.mark.parametrize(
    "email",
    ["invalid", "user@", "@mail.ru", "user@mail", "user@@mail.ru"],
)
def test_login_rejects_invalid_email(email):
    assert_invalid(
        LoginDTO,
        {
            "email": email,
            "password": PASSWORD,
        },
        "email",
    )

def test_login_normalizes_email_without_stripping_password():
    dto = LoginDTO.from_dict({
        "email": "  STUDENT@EXAMPLE.TEST  ",
        "password": " password with spaces ",
    })
    assert dto.email == EMAIL
    assert dto.password == " password with spaces "


@pytest.mark.parametrize("payload,field", [
    ({}, "email"),
    ({"email": EMAIL}, "password"),
    ({"email": None, "password": PASSWORD}, "email"),
    ({"email": EMAIL, "password": None}, "password"),
    ({"email": "  ", "password": PASSWORD}, "email"),
    ({"email": EMAIL, "password": ""}, "password"),
    ({"email": EMAIL, "password": 123}, "password"),
    ({"email": EMAIL, "password": PASSWORD, "extra": True}, "extra"),
])
def test_login_rejects_invalid_structure(payload, field):
    assert_invalid(LoginDTO, payload, field)


@pytest.mark.parametrize("payload", [None, [], "hello", True])
def test_login_requires_json_object(payload):
    assert_invalid(LoginDTO, payload, "body")


def test_login_does_not_apply_registration_password_length_rules():
    # Login validates credentials, not the registration length policy.
    dto = LoginDTO.from_dict({"email": EMAIL, "password": "x"})
    assert dto.password == "x"
