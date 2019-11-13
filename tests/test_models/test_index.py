import cacheorm as co
import pytest


class NoopModel(co.Model):
    class Meta:
        backend = None
        serializer = None


def test_primary_key_index_default_formatter():
    class Test(NoopModel):
        id = co.IntegerField(primary_key=True)

    key = co.CacheBuilder(Test, row={"id": 1}).build_key()
    assert "1" in key and Test._meta.name in key
    with pytest.raises(ValueError):
        co.CacheBuilder(Test, row=None).build_key()


def test_primary_key_index_string_formatter():
    class Test(NoopModel):
        id = co.IntegerField(primary_key=True, index_formatter="t.%d")

    assert "t.1" == co.CacheBuilder(Test, row={"id": 1}).build_key()


def test_primary_key_index_callable_formatter():
    class Test(NoopModel):
        id = co.IntegerField(
            primary_key=True, index_formatter=lambda *values: "callable.t.%d" % values
        )

    assert "callable.t.1" == co.CacheBuilder(Test, row={"id": 1}).build_key()
