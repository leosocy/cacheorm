class CacheBackend(object):

    def __init__(self, default_timeout=600):
        self.default_timeout = default_timeout

    def set(self, key, value, timeout=None):
        return True

    def get(self, key):
        return None

    def delete(self, key):
        return True

    def set_many(self, mapping, timeout=None):
        rv = True
        for k, v in mapping.items():
            if not self.set(k, v, timeout):
                rv = False
        return rv

    def get_many(self, *keys):
        return [self.get(k) for k in keys]

    def delete_many(self, *keys):
        return all(self.delete(k) for k in keys)

    def has(self, key):
        raise NotImplementedError


class InMemory(CacheBackend):
    pass


class Redis(CacheBackend):
    pass


class Memcached(CacheBackend):
    pass
