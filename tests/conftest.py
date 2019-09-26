import pytest
from cacheorm.backends import SimpleBackend


@pytest.fixture()
def general_flow_test_backends():
    yield (SimpleBackend(),)
