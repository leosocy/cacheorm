# A cache-based python ORM -- supports Redis, Memcached.

[![Build Status](https://travis-ci.org/Leosocy/cacheorm.svg?branch=master)](https://travis-ci.org/Leosocy/cacheorm)
[![codecov](https://codecov.io/gh/Leosocy/cacheorm/branch/master/graph/badge.svg)](https://codecov.io/gh/Leosocy/cacheorm)

## CacheBackend

- BaseBackend
- SimpleBackend
- RedisBackend
- MemcachedBackend

### Methods

- `set(key, value)`
- `get(key)`
- `delete(key)`
- `set_many(mapping)`
- `get_many(*keys)`
- `delete_many(*keys)`
- `has(key)`

## ModelBase

## Serializer

- json
- msgpack
- pickle

### Registry
