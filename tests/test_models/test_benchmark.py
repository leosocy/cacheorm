import pytest

from .base_models import User


@pytest.fixture()
def user_model(serializer, backend):
    s, b = serializer, backend

    class TestUser(User):
        class Meta:
            serializer = s
            backend = b
            ttl = 10 * 60

    return TestUser


def test_benchmark_insert(benchmark, user_model, users_data):
    def do_insert():
        return [user_model.insert(**row).execute() for row in users_data]

    users = benchmark(do_insert)
    for user in users:
        got_user = user_model.get(id=user.id)
        assert user == got_user


def test_benchmark_insert_many(benchmark, user_model, users_data):
    def do_insert_many():
        return user_model.insert_many(*users_data).execute()

    users = benchmark(do_insert_many)
    for user in users:
        assert user == user_model.get(id=user.id)


def test_benchmark_query():
    pass


def test_benchmark_update():
    pass


def test_benchmark_delete():
    pass
