import time

import mock
from cacheorm.backends import MemcachedBackend, RedisBackend, SimpleBackend
from cacheorm.types import to_bytes


def test_general_flow_set_get_delete(general_flow_test_backends):
    import pickle

    key = "foo"
    values = ("foo.test", 1, pickle.dumps({"test": "foo"}))
    year_ttl = 365 * 24 * 60 * 60
    for value in values:
        for backend in general_flow_test_backends:
            assert backend.get(key) is None
            assert not backend.has(key)
            assert backend.set(key, value, ttl=year_ttl)
            assert to_bytes(value) == backend.get(key)
            assert backend.has(key)
            new_value = bytes("foo.test.new", encoding="utf-8")
            backend.set(key, new_value)
            assert new_value == backend.get(key)
            assert backend.delete(key)
            assert not backend.has(key)


def test_general_flow_cache_expired(general_flow_test_backends):
    key = "foo"
    value = "foo.test"
    ttl = 1
    for backend in general_flow_test_backends:
        # cache 1s, not available after 1s
        backend.set(key, value, ttl=ttl)
        assert backend.has(key)
        time.sleep(1.1 * ttl)
        assert backend.get(key) is None
        assert not backend.has(key)
        # cache never expires
        backend.set(key, value, ttl=0)
        assert backend.has(key)
        time.sleep(1.1 * ttl)
        assert to_bytes(value) == backend.get(key)
        assert backend.has(key)


def test_general_flow_set_get_delete_many(general_flow_test_backends):
    mapping = {"foo": "foo.test", "bar": "bar.test", "baz": "baz.test"}
    keys = list(mapping.keys())
    for backend in general_flow_test_backends:
        values = backend.get_many(*keys)
        assert len(mapping) == len(values)
        for v in values:
            assert v is None
        assert backend.set_many(mapping)
        assert list(map(to_bytes, mapping.values())) == backend.get_many(*keys)
        for k in keys:
            assert backend.has(k)
        rv = backend.get_dict(*keys)
        assert {k: to_bytes(v) for k, v in mapping.items()} == rv
        values = backend.get_many(*keys, "unknown")
        assert len(mapping) + 1 == len(values)
        assert values[len(mapping)] is None
        assert backend.delete_many(*keys)
        for k in keys:
            assert not backend.has(k)


def test_simple_backend_exceeded_threshold():
    # no keys expired，randomly pop
    backend = SimpleBackend(threshold=2)
    backend.set("foo", "foo.test", ttl=0)
    backend.set("bar", "bar.test", ttl=1)
    backend.set("baz", "baz.test", ttl=0)
    assert 2 == len(backend._store)
    assert backend.has("baz")
    # bar expired, be pruned
    backend = SimpleBackend(threshold=2)
    backend.set("foo", "foo.test", ttl=0)
    backend.set("bar", "bar.test", ttl=1)
    time.sleep(1.1)
    backend.set("baz", "baz.test", ttl=0)
    assert not backend.has("bar")
    assert backend.has("baz")


def test_redis_backend_initialization(redis_client_args):
    redis_backend = RedisBackend(**redis_client_args)
    key = "test"
    redis_backend.set(key, 1)
    assert redis_backend.has(key)


def test_redis_backend_get_set_delete_many_once_io(redis_client):
    redis_backend = RedisBackend(client=redis_client)
    mapping = {"foo": "foo.test", "bar": "bar.test", "baz": "baz.test"}
    with mock.patch.object(
        redis_client, "execute_command", wraps=redis_client.execute_command
    ) as mock_execute:
        # use `MSET` when no ttl, use `Pipeline` when ttl > 0
        assert redis_backend.set_many(mapping, ttl=0)
        mock_execute.assert_called_once()
    with mock.patch.object(
        redis_client, "pipeline", waraps=redis_client.pipeline
    ) as mock_pipeline:
        assert redis_backend.set_many(mapping, ttl=600)
        mock_pipeline.assert_called_once()
    with mock.patch.object(
        redis_client, "execute_command", wraps=redis_client.execute_command
    ) as mock_execute:
        rv = redis_backend.get_many(*mapping.keys())
        assert list(map(to_bytes, mapping.values())) == rv
        mock_execute.assert_called_once()
        mock_execute.reset_mock()
        redis_backend.delete_many(*mapping.keys())
        mock_execute.assert_called_once()
        for key in mapping:
            assert not redis_backend.has(key)


def test_memcached_backend_initialization(memcached_client_args):
    memcached_backend = MemcachedBackend(**memcached_client_args)
    key = "test"
    memcached_backend.set(key, 1)
    assert memcached_backend.has(key)


def test_memcached_backend_get_set_delete_many_once_io(memcached_client):
    memcached_backend = MemcachedBackend(client=memcached_client)
    mapping = {"foo": "foo.test", "bar": "bar.test", "baz": "baz.test"}
    with mock.patch.object(
        memcached_client, "set_multi", wraps=memcached_client.set_multi
    ) as mock_set:
        assert memcached_backend.set_many(mapping)
        mock_set.assert_called_once()
    with mock.patch.object(
        memcached_client, "get_multi", wraps=memcached_client.get_multi
    ) as mock_get:
        rv = memcached_backend.get_many(*mapping.keys())
        assert list(map(to_bytes, mapping.values())) == rv
        mock_get.assert_called_once()
    with mock.patch.object(
        memcached_client, "delete_multi", wraps=memcached_client.delete_multi
    ) as mock_delete:
        memcached_backend.delete_many(*mapping.keys())
        mock_delete.assert_called_once()
        for key in mapping:
            assert not memcached_backend.has(key)
