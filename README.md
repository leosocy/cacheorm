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

You can register your own serializer, such as a Protobuf serializer with a `User` message.

```python
import cacheorm as co

co.registry.register("protobuf.user", co.ProtobufSerializer(user_pb2.User))
```

## Model

### Declare

```python
import datetime

import cacheorm as co

class User(co.Model):
    id = co.IntegerField(primary_key=True)
    name = co.StringField()
    height = co.FloatField()
    married = co.BooleanField(default=False)
    gender = co.EnumField(Gender, default=Gender.UNKNOWN)
    phones = co.ListField(co.StructField(PhoneNumber.se, PhoneNumber.de), default=[])
    created_at = co.DateTimeTZField(
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc)
    )

    class Meta:
        backend = co.RedisBackend()
        serializer = "json"


class Article(co.Model):
    id = co.IntegerField(primary_key=True)
    author = co.ForeignKeyField(User)
    title = co.StringField()
    content = co.StringField(default="")
    created_at = co.DateTimeField(default=datetime.datetime.now)
    updated_at = co.DateTimeField(default=datetime.datetime.now)

    class Meta:
        backend = co.SimpleBackend()
        serializer = "protobuf.article"
        ttl = 100 * 24 * 3600


class Collection(co.Model):
    collector = co.ForeignKeyField(User)
    article = co.ForeignKeyField(Article)
    mark = co.StringField(default="")

    class Meta:
        primary_key = co.CompositeKey("collector", "article", index_formatter="collection.%s.%d")
        backend = co.MemcachedBackend()
        serializer = "msgpack"
```

#### Meta

- primary_key
- backend
- serializer
- ttl

### Insert

```python
sam = User.create(id=1, name="Sam", height=178.8, gender=Gender.MALE)
bob = User.insert(id=2, name="Bob", height=182.4, gender=Gender.MALE).execute()
article = Article(author=sam, title="CacheORM", content="Create a article using cacheorm.")
article.save(force_insert=True)
collections = Collection.insert_many(
    {"collector": bob, "article_id": article},
    Collection(collector=sam, article=article)
).execute()
```

### Query

```python
sam = User.get(id=1)
bob = User.get_by_id(2)
article = Article.query(id=1).execute()
collections = Collection.query_many(
    {"collector_id": 1, "article_id": article.id},
    {"collector": bob, "article_id": article.id},
).execute()
```

### Update

Like `insert`, but only update field values when key exists.
Support for updating partial field values.

Note that the Cache Backend is not atomic for update operations,
so if you want to guarantee atomicity,
you need manager lock by yourself, such as with redlock.

```python
sam = User.set_by_id(1, {"height": 178.0})
bob = User.get_by_id(2)
bob.married = True
bob.save()
article = Article.update(
    id=1, title="What's new in CacheORM?"
).execute()
collections = Collection.update_many(
    {"collector_id": 1, "article_id": article.id, "mark": "mark"},
    {"collector": bob, "article_id": article.id, "mark": "Good"},
).execute()
```

### Delete

```python
User.delete_by_id(2)
User.delete(id=1).execute()
article = Article.query(id=1).execute()
Collection.delete_many(
    {"collector_id": 1, "article_id": article.id},
    {"collector_id": 2, "article_id": article.id},
).execute()
article.delete_instance()
```

## ModelHelper

### Insert

### Query

### Update

### Delete

## Fields

- UUIDField/ShortUUIDField
- IntegerField
- EnumField
- BooleanField
- FloatField
- DecimalField
- StringField
- BinaryField
- DateTimeField
- DateField
- TimeField
- TimestampField
- StructField(serializer, deserializer)
- JSONField
- ForeignKeyField
- CompositeKey

## TODO LIST

### Signals

- [ ] pre_save
- [ ] post_save
- [ ] pre_delete
- [ ] post_delete

### Compatible payload

- [ ] support changeable serializer

### ModelHelper

- [ ] preload foreign model instance
- [ ] insert many different model instances

### Bench

- [ ] MEM bench
- [ ] QPS bench

### Docs

- [ ] methods docstring
- [ ] Quick start
