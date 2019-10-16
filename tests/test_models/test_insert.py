from unittest import mock

import pytest
from cacheorm.fields import IntegerField, StringField


def test_create(person_model):
    amy = person_model.create(name="Amy", height=167.5, email="Amy@gmail.com")
    sam = person_model(name="Sam", height=178.6, married=True)
    sam.save()
    assert amy != sam
    got_amy = person_model.get_by_id("Amy")
    assert got_amy == amy
    assert got_amy.email == amy.email == "Amy@gmail.com"
    assert not got_amy.married
    got_sam = person_model.get(name="Sam")
    assert got_sam.email == sam.email is None
    assert got_sam.married
    assert got_sam == person_model.get_by_id("Sam")
    with pytest.raises(ValueError, match=r"missing value"):
        person_model.create(name="Daming")


def test_create_using_parent_pk(person_model):
    class Student(person_model):
        number = StringField()

    data = {"name": "Sam", "height": 178.6, "number": "190110101"}
    sam = Student.insert(**data).execute()
    got_sam = Student.get(name="Sam")
    assert got_sam.name == sam.name
    assert got_sam.number == sam.number
    assert got_sam.height == sam.height
    assert got_sam.married is not None and not got_sam.married


def test_create_override_parent_pk(person_model):
    class Student(person_model):
        id = IntegerField(primary_key=True)
        name = StringField()

    sam = Student.create(id=1, name="Sam", height=178.6)
    got_sam = Student.get_by_id(1)
    assert got_sam == sam


def test_create_over_determined_pk(person_model):
    with pytest.raises(ValueError, match="over-determined"):

        class Student(person_model):
            id = IntegerField(primary_key=True)
            name = StringField(primary_key=True)


def test_create_false_pk(base_model):
    with pytest.raises(ValueError, match="required primary key"):

        class Student(base_model):
            class Meta:
                primary_key = False


def test_create_auto_field(base_model):
    pass


def test_create_composite_pk(base_model):
    pass


def test_insert_many(person_model):
    rows = [
        {"name": "Sam", "height": 178.6, "number": "190110101"},
        person_model(name="Amy", height=167.5, married=True),
    ]
    with mock.patch.object(
        person_model._meta.backend,
        "set_many",
        wraps=person_model._meta.backend.set_many,
    ) as mock_set_many:
        insts = person_model.insert_many(rows).execute()
        assert insts[0] == person_model.get_by_id("Sam")
        assert insts[1] == person_model.get_by_id("Amy")
        mock_set_many.assert_called_once()


def test_insert_many_empty(person_model):
    with pytest.raises(ValueError):
        person_model.insert_many({}).execute()

    with mock.patch.object(
        person_model._meta.backend,
        "set_many",
        wraps=person_model._meta.backend.set_many,
    ) as mock_set_many:
        person_model.insert_many([])
        mock_set_many.assert_not_called()
