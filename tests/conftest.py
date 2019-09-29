import os

import pytest
from cacheorm.backends import MemcachedBackend, RedisBackend, SimpleBackend
from cacheorm.serializers import (
    JSONSerializer,
    MessagePackSerializer,
    PickleSerializer,
ProtobufSerializer,
    SerializerRegistry,
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


@pytest.fixture()
def general_flow_test_backends(redis_client, memcached_client):
    yield (
        SimpleBackend(),
        RedisBackend(client=redis_client),
        MemcachedBackend(client=memcached_client),
    )


@pytest.fixture()
def registry():
    registry = SerializerRegistry()
    yield registry


@pytest.fixture()
def normal_serializers(registry):
    registry.register("json", JSONSerializer())
    registry.register("msgpack", MessagePackSerializer())
    registry.register("pickle", PickleSerializer())
    yield (
        registry.get_by_name("json"),
        registry.get_by_name("msgpack"),
        registry.get_by_name("pickle"),
    )


@pytest.fixture()
def person_protobuf_serializer(registry):
    from .protos import person_pb2

    registry.register("protobuf.person", ProtobufSerializer(person_pb2.Person))
    yield registry.get_by_name("protobuf.person")


@pytest.fixture()
def person():
    from .protos import person_pb2

    return {
        "name": "John Doe",
        "id": 1234,
        "email": "jdoe@example.com",
        "phones": [{"number": "123", "type": person_pb2.Person.PhoneType.HOME},
                   {"number": "456", "type": person_pb2.Person.PhoneType.MOBILE}]
    }
