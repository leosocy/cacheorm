import pytest
from cacheorm import fields


@pytest.fixture()
def prepare_models(base_model):
    class Color(base_model):
        name = fields.StringField(primary_key=True)
        is_neutral = fields.BooleanField(default=False)


def test_color(prepare_models):
    pass
