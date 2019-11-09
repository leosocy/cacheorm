import decimal
import uuid

import cacheorm as co
import pytest

from .test_models import TestModel


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


class DecimalModel(TestModel):
    value = co.DecimalField(decimal_places=2, auto_round=True)
    value_up = co.DecimalField(
        decimal_places=2, auto_round=True, rounding=decimal.ROUND_UP, null=True
    )


def test_decimal_field():
    d1 = DecimalModel.create(value=decimal.Decimal("3"))
    d2 = DecimalModel.create(value=-3.14)
    d3 = DecimalModel.create(value=0)
    values = [
        (row.value, row.value_up)
        for row in DecimalModel.query_many(
            {"id": d1.id}, {"id": d2.id}, {"id": d3.id}
        ).execute()
    ]
    assert [
        (decimal.Decimal("3"), None),
        (decimal.Decimal("-3.14"), None),
        (decimal.Decimal("0"), None),
    ] == values
    d1 = DecimalModel.create(value=decimal.Decimal("1.2345"))
    d2 = DecimalModel.create(value=6.789)
    values = [
        (row.value, row.value_up)
        for row in DecimalModel.query_many({"id": d1.id}, {"id": d2.id}).execute()
    ]
    assert [(decimal.Decimal("1.23"), None), (decimal.Decimal("6.79"), None)] == values


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


class UUIDModel(TestModel):
    data = co.UUIDField()
    sdata = co.ShortUUIDField()


def test_uuid_field():
    uu = uuid.uuid4()
    u = UUIDModel.create(data=uu, sdata=uu)
    u_db = UUIDModel.get(id=u.id)
    assert uu == u_db.sdata
    # use hex string
    uu = uuid.uuid4()
    u = UUIDModel.create(data=uu.hex, sdata=uu.hex)
    u_db = UUIDModel.get(id=u.id)
    assert uu == u_db.data
    assert uu == u_db.sdata


class StringModel(TestModel):
    s = co.StringField(default="")
    b = co.StringField(null=True)


def test_string_field():
    s1 = StringModel.create()
    s2 = StringModel.create(s="foo", b=b"bar")
    values = [
        (row.s, row.b)
        for row in StringModel.query_many({"id": s1.id}, {"id": s2.id}).execute()
    ]
    assert [("", None), ("foo", "bar")] == values


class CompositeModel(TestModel):
    first = co.StringField()
    last = co.StringField()
    data = co.StringField()

    class Meta:
        primary_key = co.CompositeKey("first", "last", index_formatter="test.%s.%s")


def test_composite_key():
    c = CompositeModel.create(first="a", last="b", data="c")
    assert c.data == CompositeModel.get(first="a", last="b").data
    assert c.data == CompositeModel.get_by_id(("a", "b")).data
    assert c.get_id() == ("a", "b")
    with pytest.raises(TypeError):
        c._pk = {}
    with pytest.raises(ValueError):
        c._pk = ("foo", "bar", "baz")
    c._pk = ("e", "f")
    c.save(force_insert=True)
    assert c.data == CompositeModel.get_by_id(("e", "f")).data
    c = CompositeModel.set_by_id(("e", "f"), {"data": "g"})
    assert c.data == CompositeModel.get_by_id(("e", "f")).data
    CompositeModel.delete_by_id(("e", "f"))
    assert CompositeModel.get_or_none(first="e", last="f") is None
