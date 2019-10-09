import time

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

    sam = Student(name="Sam", height=178.6, number="190110101")
    sam.save()
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


def test_bulk_create(person_model):
    pass


def test_bulk_create_empty(person_model):
    pass


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
