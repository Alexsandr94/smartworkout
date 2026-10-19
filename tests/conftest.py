import pytest



@pytest.fixture
def database():
    from tests.support import TemporaryDatabase

    fixture = TemporaryDatabase()
    try:
        yield fixture
    finally:
        fixture.close()



@pytest.fixture
def exercise_repo(database, monkeypatch):
    from app.database import indexes, validators
    from app.repositories.exercises import ExerciseRepository

    monkeypatch.setattr(validators, 'get_db', lambda: database.db)
    monkeypatch.setattr(indexes, 'get_db', lambda: database.db)
    validators.ensure_schema()
    indexes.ensure_indexes()
    return ExerciseRepository(database.db)



@pytest.fixture(scope='module')
def api_server():
    from tests.support import TemporaryAPIServer

    server = TemporaryAPIServer()
    try:
        yield server
    finally:
        server.close()



@pytest.fixture
def api(api_server):
    for name in ('exercises', 'programs', 'users'):
        api_server.fixture.db[name].delete_many({})
    return api_server
