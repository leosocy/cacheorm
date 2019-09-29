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

    def __init__(self, null=False, default=None, primary_key=False, choices=None):
        self.null = null
        self.default = default
        self.primary_key = primary_key
        self.choices = choices
        self.model = None
        self.name = None

    def __hash__(self):
        return hash(
            "{model}.{field}".format(model=self.model.__name__, field=self.name)
        )

    def __repr__(self):
        if self.model and self.name:
            return "<{}: {}.{}>".format(
                type(self).__name__, self.model.__name__, self.name
            )
        return "<{}: (unbound)>".format(type(self).__name__)

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


class IntegerField(Field):
    adapt = int


class FloatField(Field):
    adapt = float


# TODO(leosocy): DecimalField


class BooleanField(Field):
    adapt = bool


class StringField(Field):
    adapt = str
