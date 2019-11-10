import uuid
from contextlib import contextmanager
from unittest import mock

import cacheorm as co


class TestModel(co.Model):
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
