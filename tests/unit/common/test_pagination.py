from bson import ObjectId
import pytest

from app.common import pagination



def test_empty_and_exact_pages_do_not_advertise_a_next_page():
    params = pagination.PaginationParams(limit=2)
    for data in ([], [{'id': 'first'}], [{'id': 'first'}, {'id': 'second'}]):
        page = pagination.paginate(data, params, key=lambda item: item.get('id'))
        assert page.data == data
        assert page.limit == 2
        assert not page.has_more
        assert page.next is None


def test_extra_item_signals_more_and_cursor_uses_last_returned_item():
    items = [{'id': 'first'}, {'id': 'second'}, {'id': 'third'}]
    page = pagination.paginate(items, pagination.PaginationParams(limit=2), key=lambda item: item.get('id'))
    assert page.data == [{'id': 'first'}, {'id': 'second'}]
    assert page.next == 'second'
    assert page.has_more
    assert len(items) == 3


def test_one_item_page_has_correct_cursor():
    page = pagination.paginate([10, 20], pagination.PaginationParams(limit=1), key=str)
    assert page.data == [10]
    assert page.next == '10'
    assert page.has_more


def test_limit_parser_accepts_boundaries_and_leading_zeros():
    for raw, expected in ((1, 1), ('1', 1), ('100', 100), ('00020', 20), ('0' * 6000 + '20', 20)):
        assert pagination.parse_limit(raw) == expected


def test_invalid_limits_do_not_reach_database_queries():
    for value in (True, 0, 101, '1_0', '1.0', '-1', 'no', '9' * 6000):
        with pytest.raises(ValueError):
            pagination.parse_limit(value)
    with pytest.raises(ValueError):
        pagination.PaginationParams(limit=0)


def test_cursor_is_retained_for_repository_traversal():
    cursor = ObjectId('507f1f77bcf86cd799439011')
    params = pagination.PaginationParams(limit=20, cursor=cursor)
    assert params.cursor == cursor
