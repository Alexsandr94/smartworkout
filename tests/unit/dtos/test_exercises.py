from bson import ObjectId
import pytest

from app.dtos import exercises
from app.dtos.base import DTOValidationError
from app.dtos.utils import validate_object_id



def valid_data():
    return {'name': 'Push-up', 'muscle_groups': ['CHEST'], 'equipment': ['BODYWEIGHT']}


def assert_invalid(dto_type, field, values):
    with pytest.raises(DTOValidationError) as caught:
        dto_type.from_dict(values)
    assert field in [error.get('field') for error in caught.value.errors]
    for error in caught.value.errors:
        assert isinstance(error.get('message'), str)
        assert error.get('message').isascii()


def test_create_required_and_boundaries():
    for field in ('name', 'muscle_groups', 'equipment'):
        values = valid_data()
        values.pop(field)
        assert_invalid(exercises.ExerciseCreateDTO, field, values)
    for field, maximum in (('name', 100), ('description', 500)):
        values = {**valid_data(), field: 'x' * maximum}
        assert exercises.ExerciseCreateDTO(**values).to_document().get(field) == 'x' * maximum
        assert_invalid(exercises.ExerciseCreateDTO, field, {**values, field: 'x' * (maximum + 1)})


def test_optional_missing_vs_null():
    result = exercises.ExerciseCreateDTO(**valid_data()).to_document()
    for field in ('description', 'video_url', 'image_url'):
        assert field not in result
        assert_invalid(exercises.ExerciseCreateDTO, field, {**valid_data(), field: None})
    assert exercises.ExerciseCreateDTO(**valid_data(), description='').to_document().get('description') == ''


def test_update_preserves_omitted_fields():
    assert exercises.ExerciseUpdateDTO().to_document() == {}
    assert exercises.ExerciseUpdateDTO(name='  Bench press  ').to_document() == {'name': 'Bench press'}
    for field in ('name', 'description', 'muscle_groups', 'equipment', 'video_url', 'image_url'):
        assert_invalid(exercises.ExerciseUpdateDTO, field, {field: None})


def test_blank_name_is_rejected():
    for value in ('', '   ', '\t\n'):
        assert_invalid(exercises.ExerciseUpdateDTO, 'name', {'name': value})


def test_enum_arrays():
    for field, valid in (('muscle_groups', 'CHEST'), ('equipment', 'DUMBBELL')):
        for invalid in ([], valid, [1], ['UNKNOWN'], [valid, None]):
            assert_invalid(exercises.ExerciseCreateDTO, field, {**valid_data(), field: invalid})
        result = exercises.ExerciseCreateDTO(**{**valid_data(), field: [valid, valid]}).to_document()
        assert result.get(field) == [valid, valid]


def test_all_contract_enum_values_are_accepted():
    muscles = ['CHEST', 'BACK', 'LEGS', 'ARMS', 'SHOULDERS', 'CORE', 'FULL_BODY']
    equipment = ['BARBELL', 'DUMBBELL', 'MACHINE', 'BODYWEIGHT', 'KETTLEBELL', 'RESISTANCE_BAND', 'OTHER']
    result = exercises.ExerciseCreateDTO(name='Circuit', muscle_groups=muscles, equipment=equipment).to_document()
    assert result.get('muscle_groups') == muscles
    assert result.get('equipment') == equipment


def test_nonstring_fields_are_rejected():
    for field in ('name', 'description', 'video_url', 'image_url'):
        for value in (1, True, [], {}):
            assert_invalid(exercises.ExerciseUpdateDTO, field, {field: value})


@pytest.mark.parametrize('field', ['video_url', 'image_url'])
@pytest.mark.parametrize('value, valid', [
    ('https://example.org/video', True),
    ('HTTP://example.org:80/video', True),
    ('https://example.org:443/video', True),
    ('http://[::1]:8000/video', True),
    ('urn:example:video', True),
    ('mailto:trainer@example.org', True),
    ('file:///tmp/image.png', True),
    ('custom://example.org:70000/video', True),
    ('https://example.org/[video]', True),
    ('https://example.org/video#part#other', True),
    ('https://example.org/%zz', True),
    ('', False),
    ('video.mp4', False),
    ('https://example.org/a b', False),
    ('https://example.org/a\tb', False),
    ('https://[broken', False),
    ('https://', False),
    ('https:///video', False),
    ('https://example.org:abc/video', False),
    ('https://example.org:0/video', False),
    ('https://example.org:65536/video', False),
    ('http://example.org:-1/video', False),
    ('urn:', False),
    ('mailto:', False),
    ('https://пример.рф/video', False),
    ("https://example.org/\x00video", False),
    ("https://example.org/\x7fvideo", False),
    ("https://:443/video", False),
])
def test_uri_validation_matches_project_rules(field, value, valid):
    for dto_type in (exercises.ExerciseCreateDTO, exercises.ExerciseUpdateDTO):
        values = valid_data() if dto_type is exercises.ExerciseCreateDTO else {}
        values[field] = value
        if valid:
            assert dto_type.from_dict(values).to_document().get(field) == value
        else:
            assert_invalid(dto_type, field, values)


def test_query_validation():
    assert exercises.ExerciseListDTO().pagination.limit == 20
    for value in ('1', '100'):
        assert exercises.ExerciseListDTO(limit=value).pagination.limit == int(value)
    for value in ('0', '101', '1.5', 'no', True, '-1', '1_0'):
        assert_invalid(exercises.ExerciseListDTO, 'limit', {'limit': value})
    query = exercises.ExerciseListDTO(muscle_group='CHEST,ARMS', equipment='DUMBBELL,BARBELL', search='жим')
    assert query.muscle_group == 'CHEST,ARMS'
    assert query.equipment == 'DUMBBELL,BARBELL'
    assert query.search == 'жим'
    for field in ('muscle_group', 'equipment'):
        for value in ('UNKNOWN', 'CHEST,' if field == 'muscle_group' else 'DUMBBELL,', 1):
            assert_invalid(exercises.ExerciseListDTO, field, {field: value})


def test_cursor_and_path_id():
    value = '507F1F77BCF86CD799439011'
    assert exercises.ExerciseListDTO(cursor=value).pagination.cursor == ObjectId(value)
    assert validate_object_id(value) == ObjectId(value)
    for invalid in ('', 'bad', 'x' * 24, '0' * 12):
        assert_invalid(exercises.ExerciseListDTO, 'cursor', {'cursor': invalid})
        with pytest.raises(DTOValidationError):
            validate_object_id(invalid)
    with pytest.raises(DTOValidationError):
        validate_object_id(None)
