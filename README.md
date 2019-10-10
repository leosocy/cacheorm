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
- TODO: FileSystemBackend

### Methods

- `set(key, value)`
- `get(key)`
- `delete(key)`
- `set_many(mapping)`
- `get_many(*keys)`
- `delete_many(*keys)`
- `has(key)`
- TODO: `add(key value)`: Store this data, only if it does not already exist.
- TODO: `replace(key, value)`: Store this data, but only if the data already exists.
- TODO: `incr/decr(key)`

## Serializer

- json
- msgpack
- pickle
- protobuf

### Registry

All serializers are registered to a registry singleton.
Provide `json`, `msgpack`, `pickle` three preset serializers.

You can register your own serializer, such as a Protobuf serializer with a `Person` message.

```python
registry.register("protobuf.person", ProtobufSerializer(person_pb2.Person))
```

## Model

### Declare

```python
import datetime
import cacheorm as co

class Person(co.Model):
    name = co.StringField(primary_key=True)
    height = co.FloatField()
    married = co.BooleanField(default=False)
    email = co.StringField(null=True)

    class Meta:
        backend = redis
        serializer = co.registry.get_by_name("json")


class Note(co.Model):
    author = co.StringField()
    title = co.StringField()
    content = co.StringField()
    created_at = co.DateTimeField(default=datetime.datetime.now)
    updated_at = co.DateTimeField(default=datetime.datetime.now)

    class Meta:
        backend = redis
        serializer = co.registry.get_by_name("protobuf.note")
        ttl = 100 * 24 * 3600


class Collection(co.Model):
    collector = co.StringField()
    note_id = co.IntegerField()

    class Meta:
        primary_key = co.CompositeField("collector", "note_id", index_formatter="collection.%s.%d")
        backend = memcached
        serializer = co.registry.get_by_name("msgpack")
```

#### Meta

- primary_key
- backend
- serializer
- ttl

### Create

```python
sam = Person.create(name="Sam", height=178.8, emial="sam@gmail.com")
bob = Person.create(name="Bob", height=182.4, emial="Bob@gmail.com")
note = Note.create(author=sam, title="CacheORM", content="Create a note using cacheorm.")
Collection.create(collector=bob, note_id=note.id)
```

### Get

### Update

### Delete

## Fields

- IntegerField
- FloatField
- TODO: DecimalField
- TODO: EnumField
- TODO: AutoField
- TODO: CompositeField
- BooleanField
- StringField
- TODO: DateTimeField
- TODO: TimestampField

## Signals
