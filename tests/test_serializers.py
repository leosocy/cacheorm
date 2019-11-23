import pytest
from cacheorm.serializers import JSONSerializer


def test_registry_register_unregister(registry):
    serializer = registry.get_by_name("json")
    assert isinstance(serializer, JSONSerializer)
    # repeat register
    with pytest.raises(ValueError):
        registry.register("json", None)
    # not found
    assert registry.get_by_name("unknown") is None
    # unregister
    registry.unregister("json")
    # repeat unregister
    with pytest.raises(KeyError):
        registry.unregister("json")
    # recover
    registry.register("json", JSONSerializer())


def test_normal_serializers_dumps_loads(serializer, user_data):
    objs = (
        1,
        1.23,
        "foo",
        "测试",
        True,
        None,
        [1, 2, 3],
        {"foo": 1, "bar": [1, 2, 3], "测试": {}},
        user_data,
    )
    for obj in objs:
        s = serializer.dumps(obj)
        assert s
        assert isinstance(s, bytes)
        o = serializer.loads(s)
        assert obj == o


def test_protobuf_serializer_dumps_loads(user_protobuf_serializer, user_data):
    from .protos import user_pb2

    user_pb = user_pb2.User(**user_data)
    for obj in (user_pb, user_data):
        s = user_protobuf_serializer.dumps(obj)
        assert s
        assert isinstance(s, bytes)
        o = user_protobuf_serializer.loads(s)
        assert user_pb == o
    with pytest.raises(TypeError):
        user_protobuf_serializer.dumps(1)
