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
- `replace(key, value)`
- `get(key)`
- `delete(key)`
- `set_many(mapping)`
- `replace_many(mapping)`
- `get_many(*keys)`
- `delete_many(*keys)`
- `has(key)`
- `incr/decr(key, delta)`
- TODO: `add(key value)`: Store this data, only if it does not already exist.

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
    remark = co.StringField(default="")

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

### Insert

```python
sam = Person.create(name="Sam", height=178.8, emial="sam@gmail.com")
bob = Person.insert(name="Bob", height=182.4, emial="Bob@gmail.com").execute()
note = Note(author=sam, title="CacheORM", content="Create a note using cacheorm.")
note.save(force_insert=True)
collections = Collection.insert_many(
    {"collector": "Bob","note_id": note.id},
    Collection(collector=sam, note_id=note.id)
).execute()
```

### Query

```python
sam = Person.get(name="Sam")
bob = Person.get_by_id("Bob")
note = Note.query(id=1).execute()
collections = Collection.query_many(
    {"collector": "Bob","note_id": note.id},
    {"collector": "Sam","note_id": note.id},
).execute()
```

### Update

Like `insert`, but only update field values when key exists.
Support for updating partial field values.

Note that the Cache Backend is not atomic for update operations,
so if you want to guarantee atomicity,
you need manager lock by yourself, such as with redlock.

```python
sam = Person.set_by_id("Sam", {"height": 178.0})
bob = Person.get_by_id("Bob")
bob.married = True
bob.save()
note = Note.update(
    id=1, title="What's new in CacheORM?"
).execute()
collections = Collection.update_many(
    {"collector": "Bob","note_id": note.id, "remark": "mark"},
    {"collector": "Sam","note_id": note.id, "remark": "Good"},
).execute()
```

### Delete

## ModelHelper

### Insert

### Query

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
