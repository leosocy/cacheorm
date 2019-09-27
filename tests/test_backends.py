import time

from cacheorm.backends import SimpleBackend


def test_general_flow_get_set_delete(general_flow_test_backends):
    key = "foo"
    value = "foo.test"
    for backend in general_flow_test_backends:
        assert backend.get(key) is None
        assert not backend.has(key)
        assert backend.set(key, value, ttl=10)
        assert value == backend.get(key)
        assert backend.has(key)
        new_value = "foo.test.new"
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
        assert value == backend.get(key)
        assert backend.has(key)


def test_general_flow_get_set_delete_many(general_flow_test_backends):
    mapping = {"foo": "foo.test", "bar": "bar.test", "baz": "baz.test"}
    keys = mapping.keys()
    for backend in general_flow_test_backends:
        values = backend.get_many(*keys)
        assert len(mapping) == len(values)
        for v in values:
            assert v is None
        assert backend.set_many(mapping)
        assert list(mapping.values()) == backend.get_many(*keys)
        for k in keys:
            assert backend.has(k)
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


def test_redis_backend_get_set_delete_many_once_io(redis_backend):
    pass
