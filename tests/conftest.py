import os

import pytest
from cacheorm.backends import MemcachedBackend, RedisBackend, SimpleBackend
from cacheorm.fields import BooleanField, FloatField, StringField
from cacheorm.models import Model
from cacheorm.serializers import (
    ProtobufSerializer,
    SerializerRegistry,
    register_preset_serializers,
)


@pytest.fixture()
def redis_client_args():
    host = os.getenv("TEST_BACKENDS_REDIS_HOST", "localhost")
    port = os.getenv("TEST_BACKENDS_REDIS_PORT", 6379)
    db = os.getenv("TEST_BACKENDS_REDIS_DB", 0)
    return {"host": host, "port": port, "db": db}


@pytest.fixture()
def redis_client(redis_client_args):
    import redis

    client = redis.Redis(**redis_client_args)
    client.flushdb()
    yield client
    client.flushdb()


@pytest.fixture()
def memcached_client_args():
    host = os.getenv("TEST_BACKENDS_MEMCACHED_HOST", "localhost")
    port = os.getenv("TEST_BACKENDS_MEMCACHED_PORT", 11211)
    return {"servers": ((host, port),)}


@pytest.fixture()
def memcached_client(memcached_client_args):
    import libmc

    client = libmc.Client(
        ["{}:{}".format(*s) for s in memcached_client_args["servers"]]
    )
    client.toggle_flush_all_feature(True)
    client.flush_all()
    yield client
    client.flush_all()


@pytest.fixture(params=("simple", "redis", "memcached"))
def backend(redis_client, memcached_client, request):
    if request.param == "simple":
        return SimpleBackend()
    elif request.param == "redis":
        return RedisBackend(client=redis_client)
    elif request.param == "memcached":
        return MemcachedBackend(client=memcached_client)


@pytest.fixture()
def registry():
    registry = SerializerRegistry()
    register_preset_serializers()
    yield registry
    registry.unregister_all()


@pytest.fixture(params=("json", "msgpack", "pickle"))
def serializer(registry, request):
    return registry.get_by_name(request.param)


@pytest.fixture()
def person_protobuf_serializer(registry):
    from .protos import person_pb2

    registry.register("protobuf.person", ProtobufSerializer(person_pb2.Person))
    yield registry.get_by_name("protobuf.person")
    registry.unregister("protobuf.person")


@pytest.fixture()
def person():
    from .protos import person_pb2

    return {
        "name": "leosocy",
        "email": "leosocy@gmail.com",
        "phones": [
            {"number": "123", "type": person_pb2.Person.PhoneType.HOME},
            {"number": "456", "type": person_pb2.Person.PhoneType.MOBILE},
        ],
    }


@pytest.fixture()
def base_model(backend, serializer):
    b = backend
    s = serializer

    class BaseModel(Model):
        class Meta:
            backend = b
            serializer = s
            ttl = 10 * 60

    return BaseModel


@pytest.fixture()
def person_model(base_model):
    class Person(base_model):
        name = StringField(primary_key=True)
        height = FloatField()
        married = BooleanField(default=False)
        email = StringField(null=True)

    return Person
