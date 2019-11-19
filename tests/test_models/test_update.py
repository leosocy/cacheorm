import pytest


def test_save_when_pk_exists(user_model):
    sam = user_model(id=1, name="Sam", height=178.6, married=True)
    # The primary key value is not empty, the force_insert is False,
    # this is the update logic, but there is no data in the cache,
    # so the save does not take effect.
    assert sam.save(force_insert=False) is False
    assert user_model.get_or_none(id=1) is None
    # Update logic, there is already data in the cache, so save takes effect.
    sam = user_model.create(id=1, name="Sam", height=178.6, married=True)
    assert user_model.get_or_none(id=1) == sam
    sam.height = 180
    assert sam.save() is True
    assert 180 == user_model.get_by_id(1).height == sam.height


def test_set_by_id(user_model):
    with pytest.raises(user_model.DoesNotExist):
        user_model.set_by_id(1, {"height": 180})
    user_model.create(id=1, name="Sam", height=178.6, married=True)
    sam = user_model.set_by_id(1, {"height": 180})
    assert 180 == user_model.get_by_id(1).height == sam.height


def test_update(user_model):
    sam = user_model.update(id=1, height=180).execute()
    assert sam is None
    user_model.create(id=1, name="Sam", height=178.6, married=True)
    sam = user_model.update(id=1, height=180).execute()
    assert 180 == user_model.get_by_id(1).height == sam.height
    with pytest.raises(ValueError):
        user_model.update(height=180).execute()


def test_update_many(user_model):
    sam, amy = user_model.update_many(
        {"id": 1, "height": 180}, {"id": 2, "married": True}
    ).execute()
    assert sam == amy is None
    user_model.create(id=2, name="Amy", height=167.5, email="Amy@gmail.com")
    sam, amy = user_model.update_many(
        {"id": 1, "height": 180}, {"id": 2, "married": True}
    ).execute()
    assert sam is None
    assert amy.height == 167.5
    assert user_model.get_by_id(2).married is True
