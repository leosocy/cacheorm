import pytest


def test_delete(person_model):
    success = person_model.delete(name="Sam").execute()
    assert success is False
    person_model.create(name="Sam", height=178.6, married=True)
    assert person_model.get_or_none(name="Sam") is not None
    success = person_model.delete(name="Sam").execute()
    assert success is True
    assert person_model.get_or_none(name="Sam") is None


def test_delete_many(person_model):
    person_model.create(name="Sam", height=178.6, married=True)
    all_success = person_model.delete_many({"name": "Sam"}, {"name": "Amy"}).execute()
    assert all_success is False
    person_model.create(name="Sam", height=178.6, married=True)
    person_model.create(name="Amy", height=167.5, email="Amy@gmail.com")
    all_success = person_model.delete_many({"name": "Sam"}, {"name": "Amy"}).execute()
    assert all_success is True


def test_delete_by_id(person_model):
    with pytest.raises(person_model.DoesNotExist):
        person_model.delete_by_id("Sam")
    person_model.create(name="Sam", height=178.6, married=True)
    assert person_model.delete_by_id("Sam") is True


def test_delete_instance(person_model):
    sam = person_model(name="Sam")
    assert sam.delete_instance() is False
    sam = person_model.create(name="Sam", height=178.6, married=True)
    assert sam.delete_instance() is True
