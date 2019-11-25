import time

import pytest


@pytest.fixture()
def inserted_users_data(user_model, users_data):
    users = user_model.insert_many(*users_data).execute()
    return {u.id: u for u in users}


def test_query(user_model, inserted_users_data):
    user = user_model.query(id=1).execute()
    assert user is not None and user == inserted_users_data[1]
    user = user_model.query(id=10).execute()
    assert user is None


def test_query_many(user_model, inserted_users_data):
    users = user_model.query_many({"id": 1}, {"id": 2}, {"id": 10}).execute()
    assert len(users) == 3
    assert users[1].id == inserted_users_data[2].id
    assert users[2] is None


def test_query_many_empty(user_model, inserted_users_data):
    users = user_model.query_many().execute()
    assert not users


def test_get_by_id(user_model, inserted_users_data):
    user = user_model.get_by_id(1)
    assert user == inserted_users_data[1]
    with pytest.raises(user_model.DoesNotExist):
        user_model.get_by_id(10)


def test_get_or_none(user_model, inserted_users_data):
    user = user_model.get_or_none(id=1)
    assert user == inserted_users_data[1]
    assert user_model.get_or_none(id=10) is None


def test_get_or_create(user_model, inserted_users_data):
    user, created = user_model.get_or_create(id=1, name="Sam", height=178.6)
    assert user == inserted_users_data[1]
    assert not created
    user, created = user_model.get_or_create(id=5, name="Susan", height=170)
    assert created
    assert user == user_model.get_by_id(5)


def test_get_when_cache_expired(user_model):
    class WrappedUser(user_model):
        class Meta:
            ttl = 1

    sam = WrappedUser.create(id=1, name="Sam", height=178.6)
    got_sam = WrappedUser.get_by_id(1)
    assert got_sam == sam
    time.sleep(1.1)
    with pytest.raises(WrappedUser.DoesNotExist):
        WrappedUser.get_by_id(1)
