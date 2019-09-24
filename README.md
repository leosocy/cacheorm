# A cache-based python ORM -- supports Redis, Memcached.


## CacheBackend

### Methods

- `set(key, value)`
- `get(key)`
- `delete(key)`
- `set_many(mapping)`
- `get_many(*keys)`
- `delete_many(*keys)`
- `has(key)`

### Backends

- BaseCache
- SimpleCache
- RedisCache
- MemcachedCache

## ModelBase

## Serializer

- json
- msgpack
- pickle

