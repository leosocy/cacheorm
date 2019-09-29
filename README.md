# A cache-based python ORM -- supports Redis, Memcached.

[![Build Status](https://travis-ci.org/Leosocy/cacheorm.svg?branch=master)](https://travis-ci.org/Leosocy/cacheorm)
[![codecov](https://codecov.io/gh/Leosocy/cacheorm/branch/master/graph/badge.svg)](https://codecov.io/gh/Leosocy/cacheorm)
[![PyPI](https://img.shields.io/pypi/v/cacheorm)](https://pypi.org/project/cacheorm/)
[![PyPI - License](https://img.shields.io/pypi/l/cacheorm)](https://github.com/Leosocy/cacheorm/blob/master/README.md)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/cacheorm)

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

## Serializer

- json
- msgpack
- pickle
- protobuf

### Registry

All serializers are registered to a registry singleton.
Provide `json`, `msgpack`, `pickle` three preset serializers.

You can register your own serializer,
such as a Protobuf serializer that registers a `Person` message.

```python
registry.register("protobuf.person", ProtobufSerializer(person_pb2.Person))
```

## ModelBase
