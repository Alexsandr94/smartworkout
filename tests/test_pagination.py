import importlib
import unittest

from bson import ObjectId


class PaginationTests(unittest.TestCase):
    def setUp(self):
        try:
            self.pagination = importlib.import_module('app.common.pagination')
        except ModuleNotFoundError:
            self.fail('Reusable pagination is not implemented')

    def test_empty_and_exact_pages_do_not_advertise_a_next_page(self):
        params = self.pagination.PaginationParams(limit=2)
        for data in ([], [{'id': 'first'}], [{'id': 'first'}, {'id': 'second'}]):
            with self.subTest(data=data):
                page = self.pagination.paginate(data, params, key=lambda item: item.get('id'))
                self.assertEqual(page.data, data)
                self.assertEqual(page.limit, 2)
                self.assertFalse(page.has_more)
                self.assertIsNone(page.next)

    def test_extra_item_signals_more_and_cursor_uses_last_returned_item(self):
        items = [{'id': 'first'}, {'id': 'second'}, {'id': 'third'}]
        page = self.pagination.paginate(items, self.pagination.PaginationParams(limit=2), key=lambda item: item.get('id'))
        self.assertEqual(page.data, [{'id': 'first'}, {'id': 'second'}])
        self.assertEqual(page.next, 'second')
        self.assertTrue(page.has_more)
        self.assertEqual(len(items), 3)

    def test_one_item_page_has_correct_cursor(self):
        page = self.pagination.paginate([10, 20], self.pagination.PaginationParams(limit=1), key=str)
        self.assertEqual(page.data, [10])
        self.assertEqual(page.next, '10')
        self.assertTrue(page.has_more)

    def test_limit_parser_accepts_boundaries_and_leading_zeros(self):
        for raw, expected in ((1, 1), ('1', 1), ('100', 100), ('00020', 20), ('0' * 6000 + '20', 20)):
            self.assertEqual(self.pagination.parse_limit(raw), expected)

    def test_invalid_limits_do_not_reach_database_queries(self):
        for value in (True, 0, 101, '1_0', '1.0', '-1', 'no', '9' * 6000):
            with self.subTest(value=str(value)[:20]), self.assertRaises(ValueError):
                self.pagination.parse_limit(value)
        with self.assertRaises(ValueError):
            self.pagination.PaginationParams(limit=0)

    def test_cursor_is_retained_for_repository_traversal(self):
        cursor = ObjectId('507f1f77bcf86cd799439011')
        params = self.pagination.PaginationParams(limit=20, cursor=cursor)
        self.assertEqual(params.cursor, cursor)
