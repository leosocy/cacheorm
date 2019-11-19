from unittest import mock

import pytest
from cacheorm.fields import IntegerField, StringField


def test_create(user_model):
    amy = user_model.create(id=1, name="Amy", height=167.5)
    assert amy.married is False
    sam = user_model(id=2, name="Sam", height=178.6, married=True)
    sam.save(force_insert=True)
    assert amy != sam
    got_amy = user_model.get_by_id(1)
    assert got_amy == amy
    assert not got_amy.married
    got_sam = user_model.get(id=2)
    assert got_sam.married
    assert got_sam == user_model.get_by_id(2)
    with pytest.raises(ValueError, match=r"missing value"):
        user_model.create(name="Daming")


def test_create_using_parent_pk(user_model):
    class Student(user_model):
        number = StringField()

    data = {"id": 1, "name": "Sam", "height": 178.6, "number": "190110101"}
    sam = Student.insert(**data).execute()
    got_sam = Student.get(id=1)
    assert got_sam.name == sam.name
    assert got_sam.number == sam.number
    assert got_sam.height == sam.height
    assert got_sam.married is not None and not got_sam.married


def test_create_override_parent_pk(user_model):
    class Student(user_model):
        id = IntegerField(primary_key=True)
        name = StringField()

    sam = Student.create(id=1, name="Sam", height=178.6)
    got_sam = Student.get_by_id(1)
    assert got_sam == sam


def test_create_over_determined_pk(user_model):
    with pytest.raises(ValueError, match="over-determined"):

        class Student(user_model):
            id = IntegerField(primary_key=True)
            name = StringField(primary_key=True)


def test_insert_many(user_model):
    rows = [
        {"id": 1, "name": "Sam", "height": 178.6, "number": "190110101"},
        user_model(id=2, name="Amy", height=167.5, married=True),
    ]
    with mock.patch.object(
        user_model._meta.backend, "set_many", wraps=user_model._meta.backend.set_many
    ) as mock_set_many:
        insts = user_model.insert_many(*rows).execute()
        assert insts[0] == user_model.get_by_id(1)
        assert insts[1] == user_model.get_by_id(2)
        mock_set_many.assert_called_once()


def test_insert_many_empty(user_model):
    with pytest.raises(ValueError):
        user_model.insert_many({}).execute()

    with mock.patch.object(
        user_model._meta.backend, "set_many", wraps=user_model._meta.backend.set_many
    ) as mock_set_many:
        user_model.insert_many()
        mock_set_many.assert_not_called()
