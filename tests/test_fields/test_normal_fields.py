import uuid

import cacheorm as co


class BaseModel(co.Model):
    id = co.ShortUUIDField(primary_key=True, default=uuid.uuid4)

    class Meta:
        backend = co.SimpleBackend()
        serializer = co.JSONSerializer()
        ttl = 60


class IntModel(BaseModel):
    value = co.IntegerField()
    value_null = co.IntegerField(null=True)


def test_integer_field():
    i1 = IntModel.create(value=1)
    i2 = IntModel.create(value=2, value_null=3)
    values = [
        (row.value, row.value_null)
        for row in IntModel.query_many({"id": i1.id}, {"id": i2.id}).execute()
    ]
    assert [(1, None), (2, 3)] == values
