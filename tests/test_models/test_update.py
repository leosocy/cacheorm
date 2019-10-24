import pytest


def test_save_when_pk_exists(person_model):
    sam = person_model(name="Sam", height=178.6, married=True)
    # The primary key value is not empty, the force_insert is False,
    # this is the update logic, but there is no data in the cache,
    # so the save does not take effect.
    assert sam.save(force_insert=False) is False
    assert person_model.get_or_none(name="Sam") is None
    # Update logic, there is already data in the cache, so save takes effect.
    sam = person_model.create(name="Sam", height=178.6, married=True)
    assert person_model.get_or_none(name="Sam") == sam
    sam.height = 180
    assert sam.save() is True
    assert person_model.get_by_id("Sam") == sam


def test_set_by_id(person_model):
    with pytest.raises(person_model.DoesNotExist):
        person_model.set_by_id("Sam", {"height": 180})
    person_model.create(name="Sam", height=178.6, married=True)
    sam = person_model.set_by_id("Sam", {"height": 180})
    assert person_model.get_by_id("Sam") == sam


def test_update(person_model):
    sam = person_model.update(name="Sam", height=180).execute()
    assert sam is None
    person_model.create(name="Sam", height=178.6, married=True)
    sam = person_model.update(name="Sam", height=180).execute()
    assert person_model.get_by_id("Sam") == sam
    with pytest.raises(ValueError, match=r"missing value"):
        person_model.update(height=180).execute()


def test_update_many(person_model):
    sam, amy = person_model.update_many(
        {"name": "Sam", "height": 180}, {"name": "Amy", "married": True}
    ).execute()
    assert sam == amy is None
    person_model.create(name="Amy", height=167.5, email="Amy@gmail.com")
    sam, amy = person_model.update_many(
        {"name": "Sam", "height": 180}, {"name": "Amy", "married": True}
    ).execute()
    assert sam is None
    assert amy.height == 167.5
    assert person_model.get_by_id("Amy") == amy
