import datetime
import decimal
import uuid

try:
    import shortuuid
except ImportError:  # pragma: no cover
    shortuuid = None


class FieldAccessor(object):
    def __init__(self, model, field, name):
        self.model = model
        self.field = field
        self.name = name

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return instance.__data__.get(self.name)
        return self.field

    def __set__(self, instance, value):
        instance.__data__[self.name] = value


class ForeignAccessor(FieldAccessor):
    def __init__(self, model, field, name):
        super(ForeignAccessor, self).__init__(model, field, name)
        self.rel_model = field.rel_model

    def get_rel_instance(self, instance):
        value = instance.__data__.get(self.name)
        if value is not None or self.name in instance.__rel__:
            if self.name not in instance.__rel__:
                obj = self.rel_model.get(**{self.field.rel_field.name: value})
                instance.__rel__[self.name] = obj
            return instance.__rel__[self.name]
        elif not self.field.null:
            raise self.rel_model.DoesNotExist
        return value

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return self.get_rel_instance(instance)
        return self.field

    def __set__(self, instance, value):
        if isinstance(value, self.rel_model):
            instance.__data__[self.name] = getattr(value, self.field.rel_field.name)
            instance.__rel__[self.name] = value
        else:
            prev_value = instance.__data__.get(self.name)
            instance.__data__[self.name] = value
            if value != prev_value and self.name in instance.__rel__:
                del instance.__rel__[self.name]


class ObjectIdAccessor(object):
    def __init__(self, field):
        self.field = field

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return instance.__data__.get(self.field.name)
        return self.field

    def __set__(self, instance, value):
        setattr(instance, self.field.name, value)


class Field(object):
    accessor_class = FieldAccessor

    def __init__(
        self,
        null=False,
        default=None,
        primary_key=False,
        index_formatter=None,
        **kwargs
    ):
        self.null = null
        self.default = default
        self.primary_key = primary_key
        if not primary_key and index_formatter is not None:
            raise ValueError("only primary_key supports setting index formatter")
        self.index_formatter = index_formatter
        self.model = None
        self.name = None

    def __hash__(self):
        return hash("%s.%s" % (self.model.__name__, self.name))

    def __repr__(self):
        if self.model and self.name:
            return "<%s: %s.%s>" % (type(self).__name__, self.model.__name__, self.name)
        return "<%s: (unbound)>" % type(self).__name__

    def __key__(self, other):
        return {self.name: other}

    def bind(self, model, name, set_attribute=True):
        self.model = model
        self.name = name
        if set_attribute:
            setattr(model, name, self.accessor_class(model, self, name))

    def adapt(self, value):
        return value

    def cache_value(self, value):
        return self.adapt(value)

    def python_value(self, value):
        return self.adapt(value)


class UUIDField(Field):
    def cache_value(self, value):
        if isinstance(value, uuid.UUID):
            return value.hex
        return uuid.UUID(value).hex

    def python_value(self, value):
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


class ShortUUIDField(UUIDField):
    def __init__(self, *args, **kwargs):
        if shortuuid is None:  # pragma: no cover
            raise ImportError("shortuuid not installed!")
        super(ShortUUIDField, self).__init__(*args, **kwargs)

    def cache_value(self, value):
        if isinstance(value, uuid.UUID):
            return shortuuid.encode(value)
        return shortuuid.encode(uuid.UUID(value))

    def python_value(self, value):
        if isinstance(value, uuid.UUID):
            return value
        return shortuuid.decode(value)


class IntegerField(Field):
    adapt = int


class EnumField(Field):
    def __init__(self, enum_class, *args, **kwargs):
        super(EnumField, self).__init__(*args, **kwargs)
        self.enum_class = enum_class

    def cache_value(self, value):
        if isinstance(value, self.enum_class):
            return value.value
        return value

    def python_value(self, value):
        return self.enum_class(value)


class FloatField(Field):
    adapt = float


class DecimalField(FloatField):
    def __init__(
        self, decimal_places=5, auto_round=False, rounding=None, *args, **kwargs
    ):
        self.decimal_places = decimal_places
        self.auto_round = auto_round
        self.rounding = rounding or decimal.DefaultContext.rounding
        super(DecimalField, self).__init__(*args, **kwargs)

    def cache_value(self, value):
        if self.auto_round:
            value = decimal.Decimal(str(value or 0))
            exp = decimal.Decimal(10) ** (-self.decimal_places)
            rounding = self.rounding
            value = value.quantize(exp, rounding=rounding)
        return super(DecimalField, self).cache_value(value)

    def python_value(self, value):
        if isinstance(value, decimal.Decimal):
            return value
        return decimal.Decimal(str(value))


class BooleanField(Field):
    def cache_value(self, value):
        return 1 if bool(value) else 0

    def python_value(self, value):
        return bool(value)


class StringField(Field):
    def adapt(self, value):
        if isinstance(value, str):
            return value
        if isinstance(value, (bytes, bytearray)):
            return value.decode(encoding="utf-8")
        return str(value)


class BinaryField(Field):
    """
    NOTE(leosocy): Since JSON and Protobuf serializer do not support binary,
     So when using these serializers, you need to set safe=True,
     then the binary will be encoded in base64.
     When using other serializers, you can set safe=False
    """

    def __init__(self, *args, safe=True, **kwargs):
        super(BinaryField, self).__init__(*args, **kwargs)
        self.safe = safe


def format_date_time(value, formats):
    for fmt in formats:
        try:
            return datetime.datetime.strptime(value, fmt)
        except ValueError:
            pass
    raise ValueError("Cannot format date time string '%s'" % value)


class _BaseFormattedField(Field):
    formats = None

    def __init__(self, formats=None, *args, **kwargs):
        if formats is not None:
            self.formats = formats
        super(_BaseFormattedField, self).__init__(*args, **kwargs)


class DateTimeField(_BaseFormattedField):
    formats = ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]

    def adapt(self, value):
        if value and isinstance(value, str):
            return format_date_time(value, self.formats)
        return value

    def cache_value(self, value):
        return str(self.adapt(value))


class DateTimeTZField(Field):
    formats = ["%Y-%m-%dT%H:%M:%S.%f%z"]

    def cache_value(self, value):
        if not isinstance(value, datetime.datetime):
            raise ValueError("datetime instance required")
        if value.tzinfo is None:
            raise ValueError("missing timezone")
        return value.astimezone(datetime.timezone.utc).strftime(self.formats[0])

    def python_value(self, value):
        if value and isinstance(value, str):
            return format_date_time(value, self.formats)
        return value


class DateField(Field):
    formats = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"]

    def adapt(self, value):
        if value and isinstance(value, str):
            return format_date_time(value, self.formats).date()
        elif value and isinstance(value, datetime.datetime):
            return value.date()
        return value

    def cache_value(self, value):
        return str(self.adapt(value))


class TimeField(Field):
    formats = [
        "%H:%M:%S.%f",
        "%H:%M:%S",
        "%H:%M",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
    ]

    def adapt(self, value):
        if value and isinstance(value, str):
            return format_date_time(value, self.formats).time()
        elif isinstance(value, datetime.datetime):
            return value.time()
        return value

    def cache_value(self, value):
        return str(self.adapt(value))


class TimestampField(Field):
    # second -> microsecond resolution
    valid_resolutions = [10 ** i for i in range(7)]

    def __init__(self, *args, **kwargs):
        self.resolution = kwargs.pop("resolution", None)
        if not self.resolution:
            self.resolution = 1
        elif self.resolution in range(2, 7):
            self.resolution = 10 ** self.resolution
        elif self.resolution not in self.valid_resolutions:
            raise ValueError(
                "TimestampField resolution must be one of: %s"
                % ", ".join(map(str, self.valid_resolutions))
            )
        self.ticks_to_microsecond = 10 ** 6 // self.resolution
        self.utc = bool(kwargs.pop("utc", False))
        now_func = datetime.datetime.utcnow if self.utc else datetime.datetime.now
        kwargs.setdefault("default", now_func)
        super(TimestampField, self).__init__(*args, **kwargs)

    def cache_value(self, value):
        if isinstance(value, datetime.date):
            value = datetime.datetime(value.year, value.month, value.day)
        if isinstance(value, datetime.datetime):
            if not self.utc:
                value = value.astimezone(datetime.timezone.utc)
            timestamp = value.timestamp()
        else:
            timestamp = value
        if self.resolution > 1:
            timestamp *= self.resolution
        return int(round(timestamp))

    def python_value(self, value):
        if self.resolution > 1:
            value, ticks = divmod(value, self.resolution)
            microseconds = int(ticks * self.ticks_to_microsecond)
        else:
            microseconds = 0
        if self.utc:
            value = datetime.datetime.utcfromtimestamp(microseconds)
        else:
            value = datetime.datetime.fromtimestamp(microseconds)
        if microseconds:
            value = value.replace(microsecond=microseconds)
        return value


class StructField(Field):
    def __init__(self, serializer, deserializer, *args, **kwargs):
        super(StructField, self).__init__(*args, **kwargs)
        self.se = serializer
        self.de = deserializer

    def cache_value(self, value):
        return self.se(value)

    def python_value(self, value):
        return self.de(value)


class JSONField(StructField):
    pass


class ForeignKeyField(Field):
    accessor_class = ForeignAccessor

    # NOTE(leosocy): 暂时不支持指定字段，因为目前query只能通过model的主键，所以目前默认外键就是关联model的主键
    #  backref也不支持，原因相同。
    # TODO(leosocy): support cascade_delete
    def __init__(self, model, object_id_name=None, *args, **kwargs):
        super(ForeignKeyField, self).__init__(*args, **kwargs)
        self.rel_model = model
        self.rel_field = None
        self.object_id_name = object_id_name

    def cache_value(self, value):
        if isinstance(value, self.rel_model):
            value = value.get_id()
        return self.rel_field.cache_value(value)

    def python_value(self, value):
        return self.rel_field.python_value(value)

    def bind(self, model, name, set_attribute=True):
        if not self.object_id_name:
            self.object_id_name = name if name.endswith("_id") else name + "_id"
        elif self.object_id_name == name:
            raise ValueError(
                "ForeignKeyField %s.%s specifies an object_id_name "
                "that conflicts with its field name" % (model._meta.name, name)
            )
        if self.rel_model == "self":
            self.rel_model = model
        self.rel_field = self.rel_model._meta.primary_key
        super(ForeignKeyField, self).bind(model, name, set_attribute)
        if set_attribute:
            setattr(model, self.object_id_name, ObjectIdAccessor(self))


class CompositeKey(Field):
    def __init__(self, *field_names, index_formatter=None, **kwargs):
        self.field_names = field_names
        super(CompositeKey, self).__init__(
            primary_key=True, index_formatter=index_formatter, **kwargs
        )

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return tuple(
                getattr(instance, field_name) for field_name in self.field_names
            )
        return self

    def __set__(self, instance, value):
        if not isinstance(value, (tuple, list)):
            raise TypeError(
                "A list or tuple must be used to set the value of "
                "a composite primary key."
            )
        if len(value) != len(self.field_names):
            raise ValueError(
                "The length of the value must equal the number "
                "of columns of the composite primary key."
            )
        for idx, field_value in enumerate(value):
            setattr(instance, self.field_names[idx], field_value)

    def __hash__(self):
        return hash((self.model.__name__, self.field_names))

    def __key__(self, other):
        return {field_name: value for field_name, value in zip(self.field_names, other)}

    def bind(self, model, name, set_attribute=True):
        self.model = model
        self.name = name
        setattr(model, self.name, self)
