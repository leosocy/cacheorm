import cacheorm as co
import pytest

from .base_models import Gender, PhoneNumber, PhoneType, User


@pytest.fixture()
def user_model(redis_client, registry):
    class TestUser(User):
        class Meta:
            backend = co.RedisBackend(client=redis_client)
            serializer = registry.get_by_name("json")
            ttl = 10 * 60

    return TestUser


@pytest.fixture()
def users_data():
    return [
        {"id": 1, "name": "Sam", "height": 178.6},
        {"id": 2, "name": "Amy", "height": 167.5, "married": True},
        {"id": 3, "name": "Daming", "height": 180, "gender": Gender.MALE},
        {
            "id": 4,
            "name": "Susan",
            "height": 160,
            "phones": [
                PhoneNumber("87878787", PhoneType.HOME),
                PhoneNumber("56565656", PhoneType.MOBILE),
            ],
        },
    ]
