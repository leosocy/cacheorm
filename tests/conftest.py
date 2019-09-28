import os

import pytest
from cacheorm.backends import MemcachedBackend, RedisBackend, SimpleBackend


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
    import pymemcache

    # Because `libmc` does not support the `flush all` operation
    # for the time being, we use `pymemcache` in the tests.
    client = pymemcache.Client(
        memcached_client_args["servers"][0], default_noreply=False
    )
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
