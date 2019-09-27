import math
import random
import time


class BaseBackend(object):  # pragma: no cover
    def __init__(self, default_ttl=600):
        self.default_ttl = default_ttl

    def _normalize_ttl(self, ttl):
        if ttl is None:
            ttl = self.default_ttl
        return int(max(ttl, 0))

    def set(self, key, value, ttl=None):
        return True

    def get(self, key):
        return None

    def delete(self, key):
        return True

    def set_many(self, mapping, ttl=None):
        rv = True
        for k, v in mapping.items():
            if not self.set(k, v, ttl):
                rv = False
        return rv

    def get_many(self, *keys):
        return [self.get(k) for k in keys]

    def get_dict(self, *keys):
        return dict(zip(keys, self.get_many(*keys)))

    def delete_many(self, *keys):
        return all(self.delete(k) for k in keys)

    def has(self, key):
        raise NotImplementedError


class SimpleBackend(BaseBackend):
    def __init__(self, threshold=100, default_ttl=300):
        super(SimpleBackend, self).__init__(default_ttl)
        self._threshold = threshold
        self._store = {}

    def _normalize_ttl(self, ttl):
        ttl = super(SimpleBackend, self)._normalize_ttl(ttl)
        return time.time() + ttl if ttl > 0 else 0

    def _randomly_select(self, ratio=0.2):
        keys = list(self._store.keys())
        random.shuffle(keys)
        return [keys[i] for i in range(math.ceil(len(keys) * ratio))]

    def _prune(self):
        if len(self._store) >= self._threshold:
            now = time.time()
            toremove = []
            for key, (expireat, _) in self._store.items():
                if expireat != 0 and expireat < now:
                    toremove.append(key)
            toremove = toremove or self._randomly_select(0.2)
            for key in toremove:
                self._store.pop(key, None)

    def set(self, key, value, ttl=None):
        expireat = self._normalize_ttl(ttl)
        self._prune()
        self._store[key] = (expireat, value)
        return True

    def get(self, key):
        try:
            expireat, value = self._store[key]
            if expireat == 0 or expireat > time.time():
                return value
        except KeyError:
            return None

    def delete(self, key):
        return self._store.pop(key, None) is not None

    def has(self, key):
        return self.get(key) is not None


class RedisBackend(BaseBackend):
    def __init__(
        self,
        host="localhost",
        port=6379,
        password=None,
        db=0,
        default_ttl=600,
        **kwargs
    ):
        super(RedisBackend, self).__init__(default_ttl)
        try:
            import redis
        except ImportError:  # pragma: no cover
            raise ModuleNotFoundError("no redis module found")
        self._client = redis.Redis(
            host=host, port=port, password=password, db=db, **kwargs
        )

    def _normalize_ttl(self, ttl):
        ttl = super(RedisBackend, self)._normalize_ttl(ttl)
        if ttl == 0:
            ttl = -1
        return ttl

    def set(self, key, value, ttl=None):
        ttl = self._normalize_ttl(ttl)
        if ttl == -1:
            return self._client.set(key, value)
        else:
            return self._client.setex(key, ttl, value)

    def get(self, key):
        value = self._client.get(key)
        if not value:
            return None
        return value.decode()

    def delete(self, key):
        return self._client.delete(key)

    def has(self, key):
        return self._client.exists(key)


class Memcached(BaseBackend):
    pass
