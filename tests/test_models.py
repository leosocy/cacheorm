def test_create(person_model):
    # sam = person_model.create(name="Sam")
    # assert person_model.get(name="Sam").email == sam.email
    amy = person_model.create(name="Amy", email="Amy@gmail.com")
    got_may = person_model.get_by_id("Amy")
    assert got_may is not amy
    assert got_may.email == amy.email == "Amy@gmail.com"


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
