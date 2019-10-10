import math
import random
import time

from .types import to_bytes


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

    # TODO(leosocy): support incr/decr add/replace


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
                return to_bytes(value)
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
        client=None,
        default_ttl=600,
        **kwargs
    ):
        super(RedisBackend, self).__init__(default_ttl)
        if client is None:
            try:
                import redis
            except ImportError:  # pragma: no cover
                raise ModuleNotFoundError("no redis module found")
            self._client = redis.Redis(
                host=host, port=port, password=password, db=db, **kwargs
            )
        else:
            self._client = client

    def _normalize_ttl(self, ttl):
        ttl = super(RedisBackend, self)._normalize_ttl(ttl)
        if ttl == 0:
            ttl = None
        return ttl

    def set(self, key, value, ttl=None):
        ttl = self._normalize_ttl(ttl)
        return self._client.set(key, value, ex=ttl)

    def get(self, key):
        return to_bytes(self._client.get(key))

    def delete(self, key):
        return self._client.delete(key)

    def set_many(self, mapping, ttl=None):
        ttl = self._normalize_ttl(ttl)
        if ttl is None:
            return self._client.mset(mapping)
        with self._client.pipeline() as pipe:
            for key, value in mapping.items():
                pipe.setex(name=key, value=value, time=ttl)
            return pipe.execute()

    def get_many(self, *keys):
        return [to_bytes(v) for v in self._client.mget(keys)]

    def delete_many(self, *keys):
        return self._client.delete(*keys)

    def has(self, key):
        return self._client.exists(key)


class MemcachedBackend(BaseBackend):
    KEY_MAX_LENGTH = 250

    def __init__(self, servers=(("localhost", 11211),), client=None, default_ttl=600):
        super(MemcachedBackend, self).__init__(default_ttl)
        if client is None:
            self._client = MemcachedBackend._import_preferred_mc_lib(servers)
            if self._client is None:  # pragma: no cover
                raise ModuleNotFoundError("no memcached module found")
        else:
            self._client = client

    def _normalize_ttl(self, ttl):
        ttl = super(MemcachedBackend, self)._normalize_ttl(ttl)
        # After 30 days, is treated as a unix timestamp of an exact date.
        if ttl >= 30 * 24 * 60 * 60:
            return int(time.time()) + ttl
        return ttl

    def set(self, key, value, ttl=None):
        ttl = self._normalize_ttl(ttl)
        return self._client.set(key, value, ttl)

    def get(self, key):
        if self._key_invalid(key):
            return None
        return to_bytes(self._client.get(key))

    def delete(self, key):
        if self._key_invalid(key):
            return False
        return self._client.delete(key)

    def set_many(self, mapping, ttl=None):
        ttl = self._normalize_ttl(ttl)
        failed_keys = self._client.set_multi(mapping, ttl)
        # return `True` if success in libmc
        # return failed_keys list in other libraries.
        return failed_keys if isinstance(failed_keys, bool) else not failed_keys

    def get_many(self, *keys):
        mapping = self.get_dict(*keys)
        return [mapping[key] for key in keys]

    def get_dict(self, *keys):
        valid_keys, _ = self._filter_valid_keys(*keys)
        mapping = self._client.get_multi(valid_keys)
        return {key: to_bytes(mapping.get(key, None)) for key in keys}

    def delete_many(self, *keys):
        valid_keys, filtered = self._filter_valid_keys(*keys)
        rv = self._client.delete_multi(valid_keys)
        if filtered:
            return False
        return rv

    def has(self, key):
        if self._key_invalid(key):
            return False
        return self._client.append(key, b"")

    @staticmethod
    def _import_preferred_mc_lib(servers):  # pragma: no cover
        """
        Looks into the following packages/modules to find bindings for memcached:

        - ``libmc``
        - ``pylibmc``
        - ``pymemcache``
        """
        try:
            import libmc
        except ImportError:
            pass
        else:
            return libmc.Client(["{}:{}".format(*server) for server in servers])

        try:
            import pylibmc
        except ImportError:
            pass
        else:
            return pylibmc.Client(["{}:{}".format(*server) for server in servers])

        try:
            import pymemcache
        except ImportError:
            pass
        else:
            return pymemcache.Client(servers[0], default_noreply=False)

    @staticmethod
    def _key_invalid(key):
        if len(key) > MemcachedBackend.KEY_MAX_LENGTH:
            return True

    @staticmethod
    def _filter_valid_keys(*keys):
        rv = []
        filtered = False
        for key in keys:
            if MemcachedBackend._key_invalid(key):
                filtered = True
                continue
            rv.append(key)
        return rv, filtered
