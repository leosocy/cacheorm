import decimal
import uuid

try:
    import shortuuid
except ImportError:
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


class Field(object):
    # TODO(leosocy): support auto_increment
    accessor_class = FieldAccessor

    # TODO(leosocy): support callable index_formatter
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
        try:
            return uuid.UUID(value).hex
        except ValueError:
            return value

    def python_value(self, value):
        if isinstance(value, uuid.UUID):
            return value
        return value if value is None else uuid.UUID(value)


class ShortUUIDField(UUIDField):
    def __init__(self, *args, **kwargs):
        if shortuuid is None:
            raise ImportError("shortuuid not installed!")
        super(ShortUUIDField, self).__init__(*args, **kwargs)

    def cache_value(self, value):
        if isinstance(value, uuid.UUID):
            return shortuuid.encode(value)
        try:
            return shortuuid.encode(uuid.UUID(value))
        except ValueError:
            return value

    def python_value(self, value):
        if isinstance(value, uuid.UUID):
            return value
        return value if value is None else shortuuid.decode(value)


class IntegerField(Field):
    adapt = int


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
        if not value:
            if value is None:
                return None
            value = decimal.Decimal()
        if self.auto_round:
            exp = decimal.Decimal(10) ** (-self.decimal_places)
            rounding = self.rounding
            value = decimal.Decimal(str(value)).quantize(exp, rounding=rounding)
        return super(DecimalField, self).cache_value(value)

    def python_value(self, value):
        if value is None:
            return value
        if isinstance(value, decimal.Decimal):
            return value
        return decimal.Decimal(str(value))


# TODO(leosocy): EnumField


class BooleanField(Field):
    adapt = bool


class StringField(Field):
    def adapt(self, value):
        if isinstance(value, str):
            return value
        if isinstance(value, bytes):
            return value.decode(encoding="utf-8")
        return str(value)


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
