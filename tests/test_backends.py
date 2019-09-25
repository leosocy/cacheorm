from cacheorm import backends


def test_backends_get():
    rv = backends.InMemory().get("test")
    assert rv is None
