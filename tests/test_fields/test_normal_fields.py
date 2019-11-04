import uuid

import cacheorm as co


class TestModel(co.Model):
    id = co.ShortUUIDField(primary_key=True, default=uuid.uuid4)

    class Meta:
        backend = co.SimpleBackend()
        serializer = co.JSONSerializer()
        ttl = 60


class IntModel(TestModel):
    value = co.IntegerField()
    value_null = co.IntegerField(null=True)


def test_integer_field():
    i1 = IntModel.create(value=1)
    i2 = IntModel.create(value="2", value_null=3)
    values = [
        (row.value, row.value_null)
        for row in IntModel.query_many({"id": i1.id}, {"id": i2.id}).execute()
    ]
    assert [(1, None), (2, 3)] == values


class FloatModel(TestModel):
    value = co.FloatField()
    value_null = co.FloatField(null=True)


def test_float_field():
    f1 = FloatModel.create(value=1.23)
    f2 = FloatModel.create(value=4.56, value_null="7.89")
    values = [
        (row.value, row.value_null)
        for row in FloatModel.query_many({"id": f1.id}, {"id": f2.id}).execute()
    ]
    assert [(1.23, None), (4.56, 7.89)] == values


class BoolModel(TestModel):
    value = co.BooleanField(null=True)


def test_boolean_field():
    b1 = BoolModel.create(value=True)
    b2 = BoolModel.create(value=False)
    b3 = BoolModel.create()
    values = [
        row.value
        for row in BoolModel.query_many(
            {"id": b1.id}, {"id": b2.id}, {"id": b3.id}
        ).execute()
    ]
    assert [True, False, None] == values
