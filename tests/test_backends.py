import time

import mock
from cacheorm.backends import MemcachedBackend, RedisBackend, SimpleBackend
from cacheorm.types import to_bytes


def test_general_flow_set_get_delete(backend):
    import pickle

    key = "foo"
    values = ("foo.test", "", 1, pickle.dumps({"test": "foo"}))
    year_ttl = 365 * 24 * 60 * 60
    for value in values:
        assert backend.get(key) is None
        assert backend.has(key) is False
        assert backend.set(key, value, ttl=year_ttl) is True
        assert to_bytes(value) == backend.get(key)
        assert backend.has(key) is True
        new_value = bytes("foo.test.new", encoding="utf-8")
        backend.set(key, new_value)
        assert new_value == backend.get(key)
        assert backend.delete(key) is True
        assert backend.has(key) is False
        assert backend.delete(key) is False


def test_general_flow_set_get_delete_many(backend):
    mapping = {"foo": "foo.test", "bar": "bar.test", "baz": "baz.test"}
    keys = list(mapping.keys())
    values = backend.get_many(*keys)
    assert len(mapping) == len(values)
    for v in values:
        assert v is None
    rv = backend.set_many(mapping)
    for k in keys:
        assert rv[k] is True
    assert list(map(to_bytes, mapping.values())) == backend.get_many(*keys)
    for k in keys:
        assert backend.has(k)
    rv = backend.get_dict(*keys)
    assert {k: to_bytes(v) for k, v in mapping.items()} == rv
    values = backend.get_many(*keys, "unknown")
    assert len(mapping) + 1 == len(values)
    assert values[-1] is None
    assert backend.delete_many(*keys[:2]) is True
    assert backend.delete_many(keys[-1], "unknown") is False
    for k in keys:
        assert not backend.has(k)


def test_general_flow_cache_expired(backend):
    key = "foo"
    value = "foo.test"
    ttl = 1
    # cache 1s, not available after 1s
    backend.set(key, value, ttl=ttl)
    backend.set_many({"bar": "bar.test", "baz": "baz.test"}, ttl=ttl)
    assert backend.has(key)
    assert backend.has("baz")
    time.sleep(1.1 * ttl)
    assert backend.get(key) is None
    assert backend.get("bar") is None
    # cache never expires
    backend.set(key, value, ttl=0)
    assert backend.has(key)
    time.sleep(1.1 * ttl)
    assert to_bytes(value) == backend.get(key)
    assert backend.has(key)


def test_general_flow_replace(backend):
    key = "foo"
    value = "foo.test"
    year_ttl = 365 * 24 * 60 * 60
    assert backend.replace(key, value, ttl=year_ttl) is False
    assert not backend.has(key)
    backend.set(key, value, ttl=year_ttl)
    assert backend.has(key)
    assert backend.replace(key, value, ttl=1) is True
    assert backend.has(key)
    time.sleep(1.1)
    assert not backend.has(key)  # assert ttl has been update to 1


def test_general_flow_replace_many(backend):
    year_ttl = 365 * 24 * 60 * 60
    mapping = {"foo": "foo.test", "bar": "bar.test", "baz": "baz.test"}
    keys = list(mapping.keys())
    assert backend.replace_many(mapping) == {k: False for k in keys}
    assert not backend.has("foo")
    backend.set("foo", mapping["foo"], ttl=year_ttl)
    rv = backend.replace_many(mapping, ttl=1)
    assert rv["foo"] is True
    assert rv["bar"] == rv["baz"] is False
    assert backend.has("foo")
    assert not backend.has("bar")
    time.sleep(1.1)
    assert not backend.has("bar")


def test_general_flow_incr_decr(backend):
    key = "foo"
    assert backend.incr(key, ttl=0) == 1
    assert backend.has(key)
    assert backend.incr(key, ttl=1) == 2
    assert backend.decr(key, ttl=1) == 1
    time.sleep(1.1)
    assert not backend.has(key)
    assert backend.incr(key, delta=10) == 10
    assert backend.decr(key, delta=11, ttl=0) == -1


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
        # use `MSET` when no ttl == 0, use `Pipeline` when ttl > 0
        assert redis_backend.set_many(mapping, ttl=0)
        mock_execute.assert_called_once()
    with mock.patch.object(
        redis_client, "pipeline", wraps=redis_client.pipeline
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
        assert redis_backend.delete_many(*mapping.keys()) is True
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


def test_memcached_backend_too_long_key_length(memcached_client):
    memcached_backend = MemcachedBackend(client=memcached_client)
    too_long_key = "a" * 251
    mapping = {"foo": "foo.test", too_long_key: "too_long"}
    assert memcached_backend.set(too_long_key, "too_long") is False
    assert memcached_backend.replace(too_long_key, "too_too_long") is False

    rv = memcached_backend.set_many(mapping)
    assert rv["foo"] is True
    assert rv[too_long_key] is False

    assert memcached_backend.get(too_long_key) is None
    rv = memcached_backend.get_dict(*mapping.keys())
    assert rv[too_long_key] is None
    assert rv["foo"]

    assert memcached_backend.has(too_long_key) is False
    assert memcached_backend.delete(too_long_key) is False
    assert memcached_backend.delete_many(*mapping.keys()) is False
    assert memcached_backend.has("foo") is False


def test_benchmark_backend_set(benchmark, backend):
    def do_set(k, v, ttl=None):
        backend.set(k, v, ttl)

    benchmark(do_set, "foo", "bar" * 100, 10 * 60)


def test_benchmark_backend_set_many(benchmark, backend):
    def do_set_many(mapping, ttl=None):
        backend.set_many(mapping, ttl)

    benchmark(do_set_many, {"foo": "bar", "bar": "baz"}, 10 * 60)


def test_benchmark_backend_get(benchmark, backend):
    def do_get(k):
        backend.get(k)

    backend.set("foo", "bar")
    benchmark(do_get, "foo")


def test_benchmark_backend_get_many(benchmark, backend):
    def do_get_many(*keys):
        backend.get_many(*keys)

    backend.set_many({"foo": "bar", "bar": "baz"}, 10 * 60)
    benchmark(do_get_many, "foo", "bar")


def test_benchmark_backend_replace(benchmark, backend):
    def do_replace(k, v, ttl=None):
        backend.replace(k, v, ttl)

    backend.set("foo", "bar")
    benchmark(do_replace, "foo", "new_bar", 10 * 60)


def test_benchmark_backend_replace_many(benchmark, backend):
    def do_replace_many(mapping, ttl=None):
        backend.replace_many(mapping, ttl)

    backend.set_many({"foo": "bar", "bar": "baz"}, 10 * 60)
    benchmark(do_replace_many, {"foo": "new_bar", "bar": "new_baz"}, 10 * 60)


def test_benchmark_backend_delete(benchmark, backend):
    def do_delete(k):
        backend.delete(k)

    backend.set("foo", "bar")
    benchmark(do_delete, "foo")


def test_benchmark_backend_delete_many(benchmark, backend):
    def do_delete_many(*keys):
        backend.delete_many(*keys)

    backend.set_many({"foo": "bar", "bar": "baz"}, 10 * 60)
    benchmark(do_delete_many, "foo", "bar")
