import os

import cacheorm as co
import pytest


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
    import pylibmc

    client = pylibmc.Client(
        ["{}:{}".format(*s) for s in memcached_client_args["servers"]]
    )
    client.flush_all()
    yield client
    client.flush_all()


@pytest.fixture(params=("simple", "redis", "memcached"))
def backend(redis_client, memcached_client, request):
    if request.param == "simple":
        return co.SimpleBackend()
    elif request.param == "redis":
        return co.RedisBackend(client=redis_client)
    elif request.param == "memcached":
        return co.MemcachedBackend(client=memcached_client)


@pytest.fixture()
def registry():
    registry = co.SerializerRegistry()
    co.register_preset_serializers()
    yield registry
    registry.unregister_all()


@pytest.fixture(params=("json", "msgpack", "pickle"))
def serializer(registry, request):
    return registry.get_by_name(request.param)


@pytest.fixture()
def user_protobuf_serializer(registry):
    from .protos import user_pb2

    registry.register("protobuf.user", co.ProtobufSerializer(user_pb2.User))
    yield registry.get_by_name("protobuf.user")
    registry.unregister("protobuf.user")


@pytest.fixture()
def user_data():
    from .protos import user_pb2

    return {
        "id": 1,
        "name": "leosocy",
        "height": 179.6,
        "gender": user_pb2.User.Gender.MALE,
        "phones": [
            {"number": "123", "type": user_pb2.User.PhoneType.HOME},
            {"number": "456", "type": user_pb2.User.PhoneType.MOBILE},
        ],
    }
