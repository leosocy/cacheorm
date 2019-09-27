import os

import pytest
from cacheorm.backends import RedisBackend, SimpleBackend


@pytest.fixture()
def redis_backend():
    host = os.getenv("TEST_BACKENDS_REDIS_HOST", "localhost")
    port = os.getenv("TEST_BACKENDS_REDIS_PORT", 6379)
    db = os.getenv("TEST_BACKENDS_REDIS_DB", 0)
    backend = RedisBackend(host=host, port=port, db=db)
    backend._client.flushdb()
    yield backend
    backend._client.flushdb()


@pytest.fixture()
def general_flow_test_backends(redis_backend):
    yield (SimpleBackend(), redis_backend)
