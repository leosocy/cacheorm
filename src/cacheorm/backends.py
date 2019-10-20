import math
import random
import time

from .types import to_bytes


class BaseBackend(object):  # pragma: no cover
    """Base class for the cache backends.
    All the cache backends implement this API or a superset of it.

    :param default_ttl: the default ttl (in seconds) that is used if
                        no ttl is specified on :meth:`set`. A ttl
                        of 0 indicates that the cache never expires.
    """

    def __init__(self, default_ttl=600):
        self.default_ttl = default_ttl

    def _normalize_ttl(self, ttl):
        if ttl is None:
            ttl = self.default_ttl
        return int(max(ttl, 0))

    def set(self, key, value, ttl=None):
        """Add a new key/value to the cache (overwrites value, if key already
        exists in the cache).

        :param key: the key to set
        :param value: the value for the key
        :param ttl: the cache ttl for the key in seconds (if not
                    specified, it uses the default ttl). A ttl of
                    0 indicates that the cache never expires.
        :returns: ``True`` if key has been updated, ``False`` for backend
                  errors.
        :rtype: boolean
        """
        return True

    def replace(self, key, value, ttl=None):
        """Replace the key/value in the cache with value
        (overwrites value only if the key already exists.).

        :param key: the key to replace
        :param value: the new value for the key
        :param ttl: the new cache ttl for the key in seconds (if not
                    specified, it uses the default ttl). A ttl of
                    0 indicates that the cache never expires.
        :returns: ``True`` if key has been replaced, ``False`` if key does not exists.
        :rtype: boolean
        """
        return True

    def get(self, key):
        """Look up key in the cache and return the value for it.

        :param key: the key to be looked up.
        :returns: The bytes(value) if it exists and is readable, else ``None``.
        """
        return None

    def delete(self, key):
        """Delete `key` from the cache.

        :param key: the key to delete.
        :returns: Whether the key existed and has been deleted.
        :rtype: boolean
        """
        return True

    def set_many(self, mapping, ttl=None):
        """Sets multiple keys and values from a mapping.

        :param mapping: a mapping with the keys/values to set.
        :param ttl: the cache ttl for the key in seconds (if not
                    specified, it uses the default ttl). A ttl of
                    0 indicates that the cache never expires.
        :returns: A dict, the keys is the keys in the mapping,
                  and the value is whether the corresponding key is updated.
                  ``True`` if key has been updated, else ``False``
        :rtype: dict
        """
        return {k: self.set(k, v, ttl) for k, v in mapping.items()}

    def replace_many(self, mapping, ttl=None):
        """Replaces multiple keys and values from a mapping.

        :param mapping: a mapping with the keys/values to replace.
        :param ttl: the cache ttl for the key in seconds (if not
                    specified, it uses the default ttl). A ttl of
                    0 indicates that the cache never expires.
        :returns: A dict, the keys is the keys in the mapping,
                  and the value is whether the corresponding key is replaced.
                  ``True`` if key has been replaced, else ``False``.
        :rtype: dict
        """
        return {k: self.replace(k, v, ttl) for k, v in mapping.items()}

    def get_many(self, *keys):
        """Returns a list of values for the given keys.
        For each key an item in the list is created.

            foo, bar = cache.get_many("foo", "bar")

        Has the same error handling as :meth:`get`.

        :param keys: The function accepts multiple keys as positional arguments.
        :rtype: list
        """
        return [self.get(k) for k in keys]

    def get_dict(self, *keys):
        """Like :meth:`get_many` but return a dict::

            d = cache.get_dict("foo", "bar")
            foo = d["foo"]
            bar = d["bar"]

        :param keys: The function accepts multiple keys as positional
                     arguments.
        """
        return dict(zip(keys, self.get_many(*keys)))

    def delete_many(self, *keys):
        """Deletes multiple keys at once.

        :param keys: The function accepts multiple keys as positional
                     arguments.
        :returns: Whether all given keys have been deleted.
        :rtype: boolean
        """
        return all(self.delete(k) for k in keys)

    def has(self, key):
        """Checks if a key exists in the cache without returning it. This is a
        cheap operation that bypasses loading the actual data on the backend.

        This method is optional and may not be implemented on all caches.

        :param key: the key to check
        """
        raise NotImplementedError

    def incr(self, key, delta=1, ttl=None):
        """Increments the value of a key by `delta`. If the key key does
        not exist, its value will be initialized to 0 first, and
        then the `incr` will be executed again.

        For supporting caches this is an atomic operation.

        :param key: the key to increment.
        :param delta: the delta to add.
        :param ttl: the cache ttl for the key in seconds (if not
                    specified, it uses the default ttl). A ttl of
                    0 indicates that the cache never expires.
        :returns: The new value or ``None`` for backend errors.
        """
        value = int(self.get(key) or 0) + delta
        return value if self.set(key, value, ttl) else None

    def decr(self, key, delta=1, ttl=None):
        """Decrements the value of a key by `delta`.  If the key key does
        not exist, its value will be initialized to 0 first, and
        then the `decr` will be executed again.

        For supporting caches this is an atomic operation.

        :param key: the key to increment.
        :param delta: the delta to subtract.
        :param ttl: the cache ttl for the key in seconds (if not
                    specified, it uses the default ttl). A ttl of
                    0 indicates that the cache never expires.
        :returns: The new value or `None` for backend errors.
        """
        value = int(self.get(key) or 0) - delta
        return value if self.set(key, value, ttl) else None


class SimpleBackend(BaseBackend):
    """Simple backend for single process environments.  This class exists
    mainly for the development server and is not 100% thread safe.  It tries
    to use as many atomic operations as possible and no locks for simplicity
    but it could happen under heavy load that keys are added multiple times.

    :param threshold: the maximum number of items the cache stores before
                      it starts deleting some.
    :param default_ttl: the default ttl that is used if no ttl is
                        specified on :meth:`~BaseBackend.set`. A ttl of
                        0 indicates that the cache never expires.
    """

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

    def replace(self, key, value, ttl=None):
        if key not in self._store:
            return False
        expireat = self._normalize_ttl(ttl)
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
    """Uses the Redis key-value store as a cache backend.

    :param host: address string of the Redis server.
    :param port: port number on which Redis server listens for connections.
    :param password: password authentication for the Redis server.
    :param db: db (zero-based numeric index) on Redis Server to connect.
    :param client: an object resembling an instance of a redis.Redis class.
    :param default_ttl: the default ttl that is used if no ttl is
                            specified on :meth:`~BaseBackend.set`. A ttl of
                            0 indicates that the cache never expires.

    Any additional keyword arguments will be passed to ``redis.Redis``.
    """

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
        return bool(self._client.set(key, value, ex=ttl))

    def replace(self, key, value, ttl=None):
        ttl = self._normalize_ttl(ttl)
        return bool(self._client.set(key, value, ex=ttl, xx=True))

    def get(self, key):
        return to_bytes(self._client.get(key))

    def delete(self, key):
        return bool(self._client.delete(key))

    def set_many(self, mapping, ttl=None):
        ttl = self._normalize_ttl(ttl)
        if ttl is None:
            self._client.mset(mapping)
            return {k: True for k in mapping}
        with self._client.pipeline() as pipe:
            keys = list(mapping.keys())
            for key in keys:
                pipe.set(name=key, value=mapping[key], ex=ttl)
            values = pipe.execute()
            return dict(zip(keys, values))

    def replace_many(self, mapping, ttl=None):
        ttl = self._normalize_ttl(ttl)
        with self._client.pipeline() as pipe:
            keys = list(mapping.keys())
            for key in keys:
                pipe.set(name=key, value=mapping[key], ex=ttl, xx=True)
            values = pipe.execute()
            return dict(zip(keys, map(bool, values)))

    def get_many(self, *keys):
        return [to_bytes(v) for v in self._client.mget(keys)]

    def delete_many(self, *keys):
        return self._client.delete(*keys) == len(keys)

    def has(self, key):
        return bool(self._client.exists(key))

    def incr(self, key, delta=1, ttl=None):
        ttl = self._normalize_ttl(ttl)
        if ttl is None:
            return self._client.incr(key, delta)
        with self._client.pipeline() as pipe:
            pipe.incr(key, delta)
            pipe.expire(key, ttl)
            values = pipe.execute()
            return values[0]

    def decr(self, key, delta=1, ttl=None):
        ttl = self._normalize_ttl(ttl)
        if ttl is None:
            return self._client.decr(key, delta)
        with self._client.pipeline() as pipe:
            pipe.decr(key, delta)
            pipe.expire(key, ttl)
            values = pipe.execute()
            return values[0]


class MemcachedBackend(BaseBackend):
    """A cache that uses memcached as backend.

    Implementation notes: All methods have processed the key over 250 characters,
    ensure that no errors will be thrown, ignoring the operation of illegal keys.

    :param servers: a list or tuple of server addresses or alternatively
                    a :class:`memcache.Client` or a compatible client.
    :param client: an object that resembles the API of a :class:`memcache.Client`
                   or a compatible client.
    :param default_ttl: the default ttl that is used if no ttl is
                            specified on :meth:`~BaseBackend.set`. A ttl of
                            0 indicates that the cache never expires.
    """

    KEY_MAX_LENGTH = 250

    def __init__(self, servers=(("localhost", 11211),), client=None, default_ttl=600):
        super(MemcachedBackend, self).__init__(default_ttl)
        if client is None:
            try:
                import pylibmc
            except ImportError:  # pragma: no cover
                raise ModuleNotFoundError("no memcached module found")
            self._client = pylibmc.Client(
                ["{}:{}".format(*server) for server in servers]
            )
        else:
            self._client = client

    def _normalize_ttl(self, ttl):
        ttl = super(MemcachedBackend, self)._normalize_ttl(ttl)
        # After 30 days, is treated as a unix timestamp of an exact date.
        if ttl >= 30 * 24 * 60 * 60:
            return int(time.time()) + ttl
        return ttl

    def set(self, key, value, ttl=None):
        if self._key_invalid(key):
            return False
        ttl = self._normalize_ttl(ttl)
        return self._client.set(key, value, ttl)

    def replace(self, key, value, ttl=None):
        if self._key_invalid(key):
            return False
        ttl = self._normalize_ttl(ttl)
        return self._client.replace(key, value, ttl)

    def get(self, key):
        if self._key_invalid(key):
            return None
        return to_bytes(self._client.get(key))

    def delete(self, key):
        if self._key_invalid(key):
            return False
        return self._client.delete(key)

    def set_many(self, mapping, ttl=None):
        valid_mapping = {k: v for k, v in mapping.items() if not self._key_invalid(k)}
        failed_keys = []
        if valid_mapping:
            ttl = self._normalize_ttl(ttl)
            failed_keys = self._client.set_multi(valid_mapping, ttl)
        return {k: k in valid_mapping and k not in failed_keys for k in mapping}

    def get_many(self, *keys):
        mapping = self.get_dict(*keys)
        return [mapping[key] for key in keys]

    def get_dict(self, *keys):
        valid_keys = [k for k in keys if not self._key_invalid(k)]
        mapping = self._client.get_multi(valid_keys)
        return {key: to_bytes(mapping.get(key, None)) for key in keys}

    def delete_many(self, *keys):
        valid_keys = [k for k in keys if not self._key_invalid(k)]
        rv = self._client.delete_multi(valid_keys)
        return len(valid_keys) == len(keys) and rv

    def has(self, key):
        if self._key_invalid(key):
            return False
        return self._client.append(key, b"")

    @staticmethod
    def _key_invalid(key):
        return len(key) > MemcachedBackend.KEY_MAX_LENGTH
