import pytest
from cacheorm.serializers import JSONSerializer


def test_registry(registry):
    registry.register("json", JSONSerializer())
    serializer = registry.get_by_name("json")
    assert isinstance(serializer, JSONSerializer)
    # repeat register
    with pytest.raises(ValueError):
        registry.register("json", None)
        assert registry.get_by_name("json") is not None
    # not found
    assert registry.get_by_name("unknown") is None


def test_serializers_dumps_loads(serializers):
    objs = (
        1,
        1.23,
        "foo",
        "测试",
        True,
        None,
        [1, 2, 3],
        {"foo": 1, "bar": [1, 2, 3], "测试": {}},
    )
    for obj in objs:
        for serializer in serializers:
            s = serializer.dumps(obj)
            assert s
            assert isinstance(s, bytes)
            o = serializer.loads(s)
            assert obj == o
