import datetime
import decimal
import enum
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


class E(enum.Enum):
    A = 1
    B = "b"
    C = 2.3


class EnumModel(TestModel):

    value = co.EnumField(E)
    value_null = co.EnumField(E, null=True)


def test_enum_field():
    e1 = EnumModel.create(value=1)
    e2 = EnumModel.create(value="b", value_null=E.C)
    values = [
        (row.value, row.value_null)
        for row in EnumModel.query_many({"id": e1.id}, {"id": e2.id}).execute()
    ]
    assert [(E.A, None), (E.B, E.C)] == values


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
    b2 = BoolModel.create(value=0)
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
    u_cache = UUIDModel.get(id=u.id)
    assert uu == u_cache.sdata
    # use hex string
    uu = uuid.uuid4()
    u = UUIDModel.create(data=uu.hex, sdata=uu.hex)
    u_cache = UUIDModel.get(id=u.id)
    assert uu == u_cache.data
    assert uu == u_cache.sdata


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


class DateModel(TestModel):
    d = co.DateField(null=True)
    t = co.TimeField(null=True)
    dt = co.DateTimeField(null=True)


def test_date_fields():
    dt1 = datetime.datetime(2020, 1, 1, 10, 11, 12, 34567)
    dt2 = datetime.datetime(2020, 1, 1, 10, 11, 12)
    d1 = datetime.date(2020, 1, 1)
    t1 = datetime.time(10, 11, 12, 34567)
    t2 = datetime.time(10, 11, 12)
    dm1 = DateModel.create(d=d1, t=t1, dt=dt1)
    dm2 = DateModel.create(d=None, t=t2, dt=dt2)
    dm1_cache = DateModel.get_by_id(dm1.id)
    assert (d1, t1, dt1) == (dm1_cache.d, dm1_cache.t, dm1_cache.dt)
    dm2_cache = DateModel.get_by_id(dm2.id)
    assert (None, t2, dt2) == (dm2_cache.d, dm2_cache.t, dm2_cache.dt)
    with pytest.raises(ValueError):
        DateModel.create(d="2020 01 01")


class CustomDateTimeModel(TestModel):
    dt = co.DateTimeField(formats=["%m/%d/%Y %I:%M %p", "%Y-%m-%d %H:%M:%S"])


def test_date_time_custom_format():
    m = CustomDateTimeModel.create(dt="01/01/2020 10:11 AM")
    m_cache = CustomDateTimeModel.get_by_id(m.id)
    assert datetime.datetime(2020, 1, 1, 10, 11, 0) == m_cache.dt


class DTTZModel(TestModel):
    dt = co.DateTimeTZField()


def test_date_time_tz_field():
    # miss tzinfo
    with pytest.raises(ValueError):
        DTTZModel.create(dt=datetime.datetime.now())
    tz1 = datetime.timezone.utc
    dt1 = datetime.datetime.now(tz1)
    tz2 = datetime.timezone(datetime.timedelta(hours=8))
    dt2 = datetime.datetime.now(tz2)
    # value must be datetime instance
    with pytest.raises(ValueError):
        DTTZModel.create(dt=dt1.isoformat())
    # DateTime with time zone will be converted to utc when to cache value.
    m1 = DTTZModel.create(dt=dt1)
    m1_cache = DTTZModel.get_by_id(m1.id)
    assert dt1 == m1_cache.dt
    assert m1_cache.dt.tzinfo == datetime.timezone.utc
    m2 = DTTZModel.create(dt=dt2)
    m2_cache = DTTZModel.get_by_id(m2.id)
    assert dt2 == m2_cache.dt
    assert m2_cache.dt.tzinfo == datetime.timezone.utc


class TSModel(TestModel):
    s = co.TimestampField()
    ms = co.TimestampField(resolution=3)
    us = co.TimestampField(resolution=10 ** 6)
    utc = co.TimestampField(null=True, utc=True)


def test_timestamp_field():
    dt = datetime.datetime(2020, 1, 1, 10, 11, 12).replace(microsecond=12345)
    ts = TSModel.create(s=dt, ms=dt, us=dt, u=dt)
    ts_cache = TSModel.get_by_id(ts.id)
    assert dt.replace(microsecond=0) == ts_cache.s == ts_cache.utc
    assert dt.replace(microsecond=12000) == ts_cache.ms
    assert dt == ts_cache.us


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
