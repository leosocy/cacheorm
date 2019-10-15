import time

import pytest


@pytest.fixture()
def person_data(person_model):
    persons = person_model.insert_many(
        [
            {"name": "Sam", "height": 178.6},
            {"name": "Amy", "height": 167.5, "email": "Amy@gmail.com"},
            {"name": "Daming", "height": 180, "married": True},
        ]
    ).execute()
    return {p.name: p for p in persons}


def test_query(person_model, person_data):
    person = person_model.query(name="Sam").execute()
    assert person is not None and person == person_data["Sam"]
    person = person_model.query(name="Unknown").execute()
    assert person is None


def test_query_many(person_model, person_data):
    persons = person_model.query_many(
        [{"name": "Sam"}, {"name": "Daming"}, {"name": "Unknown"}]
    ).execute()
    assert len(persons) == 3
    assert persons[1] == person_data["Daming"]
    assert persons[2] is None


def test_query_many_empty(person_model, person_data):
    persons = person_model.query_many([]).execute()
    assert not persons


def test_get_by_id(person_model, person_data):
    person = person_model.get_by_id("Sam")
    assert person == person_data["Sam"]
    with pytest.raises(person_model.DoesNotExist):
        person_model.get_by_id("Unknown")


def test_get_or_none(person_model, person_data):
    person = person_model.get_or_none(name="Sam")
    assert person == person_data["Sam"]
    assert person_model.get_or_none(name="Unknown") is None


def test_get_or_create(person_model, person_data):
    person, created = person_model.get_or_create(name="Sam", height=178.6)
    assert person == person_data["Sam"]
    assert not created
    person, created = person_model.get_or_create(name="Susan", height=170)
    assert created
    assert person == person_model.get_by_id("Susan")


def test_get_when_cache_expired(person_model):
    class WrappedPerson(person_model):
        class Meta:
            ttl = 1

    sam = WrappedPerson.create(name="Sam", height=178.6)
    got_sam = WrappedPerson.get_by_id("Sam")
    assert got_sam == sam
    time.sleep(1.1)
    with pytest.raises(WrappedPerson.DoesNotExist):
        WrappedPerson.get_by_id("Sam")
