import uuid
from contextlib import contextmanager
from unittest import mock

import cacheorm as co


class BaseModel(co.Model):
    id = co.ShortUUIDField(primary_key=True, default=uuid.uuid4)

    class Meta:
        backend = co.SimpleBackend()
        serializer = co.JSONSerializer()
        ttl = 60

    @classmethod
    @contextmanager
    def mock_backend_method(cls, method_name):
        method = getattr(cls._meta.backend, method_name)
        patch = mock.patch.object(cls._meta.backend, method_name, wraps=method)
        try:
            yield patch.start()
        finally:
            patch.stop()


class User(BaseModel):
    username = co.StringField()
    sub_user = co.ForeignKeyField("self", null=True, object_id_name="sub")


class Article(BaseModel):
    author = co.ForeignKeyField(User)
    content = co.StringField()


class Collection(BaseModel):
    collector = co.ForeignKeyField(User)
    article = co.ForeignKeyField(Article)
    mark = co.StringField(default="")

    class Meta:
        primary_key = co.CompositeKey(
            "collector", "article", index_formatter="collection.%s.%s"
        )
