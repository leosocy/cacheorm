import pytest


def test_create(person_model):
    amy = person_model.create(name="Amy", height=167.5, email="Amy@gmail.com")
    got_amy = person_model.get_by_id("Amy")
    assert got_amy == amy
    assert got_amy.email == amy.email == "Amy@gmail.com"
    assert not got_amy.married
    sam = person_model.create(name="Sam", height=178.6, married=True)
    got_sam = person_model.get(name="Sam")
    assert got_sam.email == sam.email is None
    assert got_sam.married
    assert got_sam == person_model.get_by_id("Sam")
    with pytest.raises(ValueError):
        person_model.create(name="Daming")


def test_create_parent_pk(person_model):
    pass


def test_create_no_pk(base_model):
    pass


def test_create_auto_field(base_model):
    pass


def test_bulk_create(person_model):
    pass


def test_bulk_create_empty(person_model):
    pass
