import pytest


def test_delete(user_model):
    success = user_model.delete(id=1).execute()
    assert success is False
    user_model.create(id=1, name="Sam", height=178.6, married=True)
    assert user_model.get_or_none(id=1) is not None
    success = user_model.delete(id=1).execute()
    assert success is True
    assert user_model.get_or_none(id=1) is None


def test_delete_many(user_model):
    user_model.create(id=1, name="Sam", height=178.6, married=True)
    all_success = user_model.delete_many({"id": 1}, {"id": "2"}).execute()
    assert all_success is False
    user_model.create(id=1, name="Sam", height=178.6, married=True)
    user_model.create(id=2, name="Amy", height=167.5, email="Amy@gmail.com")
    all_success = user_model.delete_many({"id": 1}, {"id": "2"}).execute()
    assert all_success is True


def test_delete_by_id(user_model):
    with pytest.raises(user_model.DoesNotExist):
        user_model.delete_by_id(1)
    user_model.create(id=1, name="Sam", height=178.6, married=True)
    assert user_model.delete_by_id(1) is True


def test_delete_instance(user_model):
    sam = user_model(id=1, name="Sam")
    assert sam.delete_instance() is False
    sam = user_model.create(id=1, name="Sam", height=178.6, married=True)
    assert sam.delete_instance() is True
