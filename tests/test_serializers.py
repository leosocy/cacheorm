import pytest
from cacheorm.serializers import JSONSerializer


def test_registry(registry):
    registry.register("json", JSONSerializer())
    serializer = registry.get_by_name("json")
    assert isinstance(serializer, JSONSerializer)
    # repeat register
    with pytest.raises(ValueError):
        registry.register("json", None)
    # not found
    assert registry.get_by_name("unknown") is None


def test_normal_serializers_dumps_loads(normal_serializers, person):
    objs = (
        1,
        1.23,
        "foo",
        "测试",
        True,
        None,
        [1, 2, 3],
        {"foo": 1, "bar": [1, 2, 3], "测试": {}},
        person,
    )
    for obj in objs:
        for serializer in normal_serializers:
            s = serializer.dumps(obj)
            assert s
            assert isinstance(s, bytes)
            o = serializer.loads(s)
            assert obj == o


def test_protobuf_serializer_dumps_loads(person_protobuf_serializer, person):
    from .protos import person_pb2

    person_pb = person_pb2.Person(**person)
    for obj in (person_pb, person):
        s = person_protobuf_serializer.dumps(obj)
        assert s
        assert isinstance(s, bytes)
        o = person_protobuf_serializer.loads(s)
        assert person_pb == o
    with pytest.raises(TypeError):
        person_protobuf_serializer.dumps(1)
