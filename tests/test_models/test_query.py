import time

import pytest


@pytest.fixture()
def user_data(user_model):
    users = user_model.insert_many(
        {"name": "Sam", "height": 178.6},
        {"name": "Amy", "height": 167.5, "email": "Amy@gmail.com"},
        {"name": "Daming", "height": 180, "married": True},
    ).execute()
    return {u.name: u for u in users}


def test_query(user_model, user_data):
    user = user_model.query(name="Sam").execute()
    assert user is not None and user == user_data["Sam"]
    user = user_model.query(name="Unknown").execute()
    assert user is None


def test_query_many(user_model, user_data):
    users = user_model.query_many(
        {"name": "Sam"}, {"name": "Daming"}, {"name": "Unknown"}
    ).execute()
    assert len(users) == 3
    assert users[1] == user_data["Daming"]
    assert users[2] is None


def test_query_many_empty(user_model, user_data):
    users = user_model.query_many().execute()
    assert not users


def test_get_by_id(user_model, user_data):
    user = user_model.get_by_id("Sam")
    assert user == user_data["Sam"]
    with pytest.raises(user_model.DoesNotExist):
        user_model.get_by_id("Unknown")


def test_get_or_none(user_model, user_data):
    user = user_model.get_or_none(name="Sam")
    assert user == user_data["Sam"]
    assert user_model.get_or_none(name="Unknown") is None


def test_get_or_create(user_model, user_data):
    user, created = user_model.get_or_create(name="Sam", height=178.6)
    assert user == user_data["Sam"]
    assert not created
    user, created = user_model.get_or_create(name="Susan", height=170)
    assert created
    assert user == user_model.get_by_id("Susan")


def test_get_when_cache_expired(user_model):
    class WrappedUser(user_model):
        class Meta:
            ttl = 1

    sam = WrappedUser.create(name="Sam", height=178.6)
    got_sam = WrappedUser.get_by_id("Sam")
    assert got_sam == sam
    time.sleep(1.1)
    with pytest.raises(WrappedUser.DoesNotExist):
        WrappedUser.get_by_id("Sam")
