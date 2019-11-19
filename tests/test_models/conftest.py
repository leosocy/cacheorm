import cacheorm as co
import pytest

from .base_models import User


@pytest.fixture()
def user_model(redis_client, registry):
    class TestUser(User):
        class Meta:
            backend = co.RedisBackend(client=redis_client)
            serializer = registry.get_by_name("json")
            ttl = 10 * 60

    return TestUser
