import cacheorm as co
import pytest


class NoopModel(co.Model):
    class Meta:
        backend = None
        serializer = None


def test_primary_key_index_default_formatter():
    class Test(NoopModel):
        id = co.IntegerField(primary_key=True)

    index = Test._index_manager.get_primary_key_index()
    assert isinstance(index, co.PrimaryKeyIndex)
    key = index.make_cache_key(id=1)
    assert "1" in key and Test._meta.name in key
    with pytest.raises(KeyError):
        index.make_cache_key(missing="unknown")


def test_primary_key_index_string_formatter():
    class Test(NoopModel):
        id = co.IntegerField(primary_key=True, index_formatter="t.%d")

    index = Test._index_manager.get_primary_key_index()
    assert "t.1" == index.make_cache_key(id=1)


def test_primary_key_index_callable_formatter():
    class Test(NoopModel):
        id = co.IntegerField(
            primary_key=True, index_formatter=lambda *values: "callable.t.%d" % values
        )

    index = Test._index_manager.get_primary_key_index()
    assert "callable.t.1" == index.make_cache_key(id=1)
