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
        return value if value is None else self.adapt(value)

    def python_value(self, value):
        return value if value is None else self.adapt(value)


class UUIDField(Field):
    def cache_value(self, value):
        if isinstance(value, uuid.UUID):
            return value.hex
        return uuid.UUID(value).hex

    def python_value(self, value):
        if isinstance(value, uuid.UUID):
            return value
        return value if value is None else uuid.UUID(value)


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
        return value if value is None else shortuuid.decode(value)


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
        return value if value is None else self.enum_class(value)


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
        if value is not None and self.auto_round:
            value = decimal.Decimal(str(value or 0))
            exp = decimal.Decimal(10) ** (-self.decimal_places)
            rounding = self.rounding
            value = value.quantize(exp, rounding=rounding)
        return super(DecimalField, self).cache_value(value)

    def python_value(self, value):
        if isinstance(value, decimal.Decimal):
            return value
        return value if value is None else decimal.Decimal(str(value))


class BooleanField(Field):
    adapt = bool


class StringField(Field):
    def adapt(self, value):
        if isinstance(value, str):
            return value
        if isinstance(value, (bytes, bytearray)):
            return value.decode(encoding="utf-8")
        return str(value)


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
