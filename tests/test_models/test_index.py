import pytest
from cacheorm.fields import StringField
from cacheorm.models import IndexManager, PrimaryKeyIndex


def test_primary_key_index_default_formatter(noop_person_model):
    assert isinstance(getattr(noop_person_model, "_index_manager", None), IndexManager)
    index = noop_person_model._index_manager.get_primary_key_index()
    assert isinstance(index, PrimaryKeyIndex)
    key = index.make_cache_key(name="Sam")
    assert "Sam" in key and noop_person_model._meta.name in key
    with pytest.raises(KeyError):
        index.make_cache_key(missing="unknown")


def test_primary_key_index_specify_formatter(noop_person_model):
    formatter = "Student.%s"

    class Student(noop_person_model):
        name = StringField(primary_key=True, index_formatter=formatter)

    index = Student._index_manager.get_primary_key_index()
    key = index.make_cache_key(name="Sam")
    assert formatter % ("Sam",) == key


def test_composite_primary_key_index(noop_person_model):
    pass
