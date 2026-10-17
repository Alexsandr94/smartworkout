import importlib
import unittest

from bson import ObjectId

from app.dtos.base import DTOValidationError
from app.dtos.utils import validate_object_id


class ExerciseDTOTests(unittest.TestCase):
    def setUp(self):
        try:
            self.dto = importlib.import_module('app.dtos.exercises')
        except ModuleNotFoundError as exc:
            if exc.name != 'app.dtos.exercises':
                raise
            self.fail('Exercises DTO validation is not implemented')

    @staticmethod
    def valid_data():
        return {'name': 'Push-up', 'muscle_groups': ['CHEST'], 'equipment': ['BODYWEIGHT']}

    def assert_invalid(self, dto_type, field, values):
        with self.assertRaises(DTOValidationError) as caught:
            dto_type.from_dict(values)
        self.assertIn(field, [error.get('field') for error in caught.exception.errors])
        for error in caught.exception.errors:
            self.assertIsInstance(error.get('message'), str)
            self.assertTrue(error.get('message').isascii())

    def test_create_required_and_boundaries(self):
        for field in ('name', 'muscle_groups', 'equipment'):
            values = self.valid_data()
            values.pop(field)
            with self.subTest(field=field):
                self.assert_invalid(self.dto.ExerciseCreateDTO, field, values)
        for field, maximum in (('name', 100), ('description', 500)):
            values = {**self.valid_data(), field: 'x' * maximum}
            self.assertEqual(self.dto.ExerciseCreateDTO(**values).to_document().get(field), 'x' * maximum)
            self.assert_invalid(self.dto.ExerciseCreateDTO, field, {**values, field: 'x' * (maximum + 1)})

    def test_optional_missing_vs_null(self):
        result = self.dto.ExerciseCreateDTO(**self.valid_data()).to_document()
        for field in ('description', 'video_url', 'image_url'):
            self.assertNotIn(field, result)
            with self.subTest(field=field):
                self.assert_invalid(self.dto.ExerciseCreateDTO, field, {**self.valid_data(), field: None})
        self.assertEqual(self.dto.ExerciseCreateDTO(**self.valid_data(), description='').to_document().get('description'), '')

    def test_update_preserves_omitted_fields(self):
        self.assertEqual(self.dto.ExerciseUpdateDTO().to_document(), {})
        self.assertEqual(self.dto.ExerciseUpdateDTO(name='  Bench press  ').to_document(), {'name': 'Bench press'})
        for field in ('name', 'description', 'muscle_groups', 'equipment', 'video_url', 'image_url'):
            with self.subTest(field=field):
                self.assert_invalid(self.dto.ExerciseUpdateDTO, field, {field: None})

    def test_blank_name_is_rejected(self):
        for value in ('', '   ', '\t\n'):
            with self.subTest(value=value):
                self.assert_invalid(self.dto.ExerciseUpdateDTO, 'name', {'name': value})

    def test_enum_arrays(self):
        for field, valid in (('muscle_groups', 'CHEST'), ('equipment', 'DUMBBELL')):
            for invalid in ([], valid, [1], ['UNKNOWN'], [valid, None]):
                with self.subTest(field=field, value=invalid):
                    self.assert_invalid(self.dto.ExerciseCreateDTO, field, {**self.valid_data(), field: invalid})
            result = self.dto.ExerciseCreateDTO(**{**self.valid_data(), field: [valid, valid]}).to_document()
            self.assertEqual(result.get(field), [valid, valid])

    def test_all_contract_enum_values_are_accepted(self):
        muscles = ['CHEST', 'BACK', 'LEGS', 'ARMS', 'SHOULDERS', 'CORE', 'FULL_BODY']
        equipment = ['BARBELL', 'DUMBBELL', 'MACHINE', 'BODYWEIGHT', 'KETTLEBELL', 'RESISTANCE_BAND', 'OTHER']
        result = self.dto.ExerciseCreateDTO(name='Circuit', muscle_groups=muscles, equipment=equipment).to_document()
        self.assertEqual(result.get('muscle_groups'), muscles)
        self.assertEqual(result.get('equipment'), equipment)

    def test_nonstring_fields_are_rejected(self):
        for field in ('name', 'description', 'video_url', 'image_url'):
            for value in (1, True, [], {}):
                with self.subTest(field=field, value=value):
                    self.assert_invalid(self.dto.ExerciseUpdateDTO, field, {field: value})

    def test_uri_scheme(self):
        for value in ('https://example.org/video', 'urn:example:video', 'mailto:trainer@example.org'):
            self.assertEqual(self.dto.ExerciseUpdateDTO(video_url=value).to_document().get('video_url'), value)
        for value in ('video.mp4', '', 'https://example.org/a b', 'https://[broken', 'https://example.org/%zz'):
            with self.subTest(value=value):
                self.assert_invalid(self.dto.ExerciseUpdateDTO, 'video_url', {'video_url': value})

    def test_uri_components(self):
        valid = ('https://[::1]:8000/a%5Bb%5D?x=/?:@#part', 'https://user:pass@example.org:443/video', 'urn:example:video', 'mailto:trainer@example.org')
        invalid = ('https://example.org:abc/video', 'https://example.org/video#part#other', 'https://example.org/[video]', 'https://user@@example.org/video', 'https://example.org?q=[video]')
        for field in ('video_url', 'image_url'):
            for value in valid:
                with self.subTest(field=field, value=value):
                    self.assertEqual(self.dto.ExerciseUpdateDTO(**{field: value}).to_document().get(field), value)
            for value in invalid:
                with self.subTest(field=field, value=value):
                    self.assert_invalid(self.dto.ExerciseUpdateDTO, field, {field: value})
                    self.assert_invalid(self.dto.ExerciseCreateDTO, field, {**self.valid_data(), field: value})

    def test_uri_authority_keeps_generic_uri_ports_and_rejects_trailing_host_text(self):
        value = 'custom://example.org:70000/video'
        with self.subTest(valid=value):
            try:
                result = self.dto.ExerciseUpdateDTO.from_dict({'video_url': value})
            except DTOValidationError:
                self.fail('A generic URI with a numeric port must be accepted')
            self.assertEqual(result.video_url, value)
        with self.subTest(invalid='trailing host text'):
            self.assert_invalid(self.dto.ExerciseUpdateDTO, 'video_url', {'video_url': 'https://[::1]junk/video'})

    def test_ipvfuture_host_rejects_percent_encoding(self):
        for value in ('custom://[v1.host%20name]/video', 'custom://[v1.host%2Fname]/video'):
            with self.subTest(value=value):
                self.assert_invalid(self.dto.ExerciseUpdateDTO, 'video_url', {'video_url': value})
        value = 'custom://[v1.host:name]/video'
        self.assertEqual(self.dto.ExerciseUpdateDTO.from_dict({'video_url': value}).video_url, value)

    def test_query_validation(self):
        self.assertEqual(self.dto.ExerciseListDTO().pagination.limit, 20)
        for value in ('1', '100'):
            self.assertEqual(self.dto.ExerciseListDTO(limit=value).pagination.limit, int(value))
        for value in ('0', '101', '1.5', 'no', True, '-1', '1_0'):
            with self.subTest(value=value):
                self.assert_invalid(self.dto.ExerciseListDTO, 'limit', {'limit': value})
        query = self.dto.ExerciseListDTO(muscle_group='CHEST,ARMS', equipment='DUMBBELL,BARBELL', search='жим')
        self.assertEqual(query.muscle_group, 'CHEST,ARMS')
        self.assertEqual(query.equipment, 'DUMBBELL,BARBELL')
        self.assertEqual(query.search, 'жим')
        for field in ('muscle_group', 'equipment'):
            for value in ('UNKNOWN', 'CHEST,' if field == 'muscle_group' else 'DUMBBELL,', 1):
                with self.subTest(field=field, value=value):
                    self.assert_invalid(self.dto.ExerciseListDTO, field, {field: value})

    def test_cursor_and_path_id(self):
        value = '507F1F77BCF86CD799439011'
        self.assertEqual(self.dto.ExerciseListDTO(cursor=value).pagination.cursor, ObjectId(value))
        self.assertEqual(validate_object_id(value), ObjectId(value))
        for invalid in ('', 'bad', 'x' * 24, '0' * 12):
            with self.subTest(value=invalid):
                self.assert_invalid(self.dto.ExerciseListDTO, 'cursor', {'cursor': invalid})
                with self.assertRaises(DTOValidationError):
                    validate_object_id(invalid)
        with self.assertRaises(DTOValidationError):
            validate_object_id(None)


if __name__ == '__main__':
    unittest.main()
