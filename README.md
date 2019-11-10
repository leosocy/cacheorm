# A cache-based python ORM -- supports Redis/Memcached/InMemory/FileSystem backends, and JSON/Msgpack/Pickle/Protobuf serializers.

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

- JSON
- Msgpack
- Pickle
- Protobuf

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

class User(co.Model):
    name = co.StringField(primary_key=True)
    height = co.FloatField()
    married = co.BooleanField(default=False)
    email = co.StringField(null=True)

    class Meta:
        backend = redis
        serializer = co.registry.get_by_name("json")


class Article(co.Model):
    id = co.IntegerField(primary_key=True)
    author = co.ForeignKeyField(User)
    title = co.StringField()
    content = co.StringField(default="")
    created_at = co.DateTimeField(default=datetime.datetime.now)
    updated_at = co.DateTimeField(default=datetime.datetime.now)

    class Meta:
        backend = redis
        serializer = co.registry.get_by_name("protobuf.article")
        ttl = 100 * 24 * 3600


class Collection(co.Model):
    collector = co.ForeignKeyField(User)
    article = co.ForeignKeyField(Article)
    mark = co.StringField(default="")

    class Meta:
        primary_key = co.CompositeKey("collector", "article", index_formatter="collection.%s.%d")
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
sam = User.create(name="Sam", height=178.8, emial="sam@gmail.com")
bob = User.insert(name="Bob", height=182.4, emial="Bob@gmail.com").execute()
article = Article(author=sam, title="CacheORM", content="Create a article using cacheorm.")
article.save(force_insert=True)
collections = Collection.insert_many(
    {"collector": bob, "article_id": article},
    Collection(collector=sam, article=article)
).execute()
```

### Query

```python
sam = User.get(name="Sam")
bob = User.get_by_id("Bob")
article = Article.query(id=1).execute()
collections = Collection.query_many(
    {"collector": "Bob", "article_id": article.id},
    {"collector": "Sam", "article_id": article.id},
).execute()
```

### Update

Like `insert`, but only update field values when key exists.
Support for updating partial field values.

Note that the Cache Backend is not atomic for update operations,
so if you want to guarantee atomicity,
you need manager lock by yourself, such as with redlock.

```python
sam = User.set_by_id("Sam", {"height": 178.0})
bob = User.get_by_id("Bob")
bob.married = True
bob.save()
article = Article.update(
    id=1, title="What's new in CacheORM?"
).execute()
collections = Collection.update_many(
    {"collector": "Bob", "article_id": article.id, "mark": "mark"},
    {"collector": "Sam", "article_id": article.id, "mark": "Good"},
).execute()
```

### Delete

```python
User.delete_by_id("Bob")
User.delete(name="Sam").execute()
article = Article.query(id=1).execute()
Collection.delete_many(
    {"collector": "Bob", "article_id": article.id},
    {"collector": "Sam", "article_id": article.id},
).execute()
article.delete_instance()
```

## ModelHelper

### Insert

### Query

### Update

### Delete

## Fields

- IntegerField
- FloatField
- DecimalField
- TODO: EnumField
- UUIDField/ShortUUIDField
- CompositeKey
- BooleanField
- StringField
- ForeignKeyField
- TODO: StructField(serializer, deserializer)
- TODO: DateTimeField
- TODO: DateField
- TODO: TimeField
- TODO: TimestampField

## Signals
