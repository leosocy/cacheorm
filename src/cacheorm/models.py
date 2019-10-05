from .fields import Field
from .types import with_metaclass


class Metadata(object):
    def __init__(self, model, backend, serializer, primary_key=None, **kwargs):
        self.model = model
        self.backend = backend
        self.serializer = serializer
        self.name = model.__name__.lower()
        self.primary_key = primary_key
        for k, v in kwargs.items():
            setattr(self, k, v)

    def add_field(self, field_name, field, set_attribute=True):
        pass

    def set_primary_key(self, name, field):
        pass

    def get_primary_keys(self):
        pass

    def set_backend(self, backend):
        pass


MODEL_BASE_NAME = "__metaclass_helper__"


class ModelBase(type):
    inheritable = {"backend", "serializer", "primary_key"}

    def __new__(cls, name, bases, attrs):
        if name == MODEL_BASE_NAME or bases[0].__name__ == MODEL_BASE_NAME:
            return super(ModelBase, cls).__new__(cls, name, bases, attrs)

        meta_options = {}
        meta = attrs.pop("Meta", None)
        if meta:
            for k, v in meta.__dict__.items():
                if not k.startswith("_"):
                    meta_options[k] = v

        pk = getattr(meta, "primary_key", None)
        pk_name = None

        # Inherit any field descriptors by deep copying the underlying field
        # into the attrs of the new model, additionally see if the bases define
        # inheritable model options and swipe them.
        for b in bases:
            if not hasattr(b, "_meta"):
                continue

            base_meta = b._meta
            for k in base_meta.__dict__:
                if k in cls.inheritable and k not in meta_options:
                    meta_options[k] = base_meta.__dict__[k]

            for (k, v) in b.__dict__.items():
                if k in attrs:
                    continue

        cls = super(ModelBase, cls).__new__(cls, name, bases, attrs)
        cls.__data__ = None
        cls._meta = Metadata(cls, **meta_options)

        fields = []
        for key, value in cls.__dict__.items():
            if isinstance(value, Field):
                if value.primary_key and pk:
                    raise ValueError("over-determined primary key {}".format(name))
                elif value.primary_key:
                    pk, pk_name = value, key
                else:
                    fields.append((key, value))
        for name, field in fields:
            cls._meta.add_field(name, field)

        cls._meta.set_primary_key(pk_name, pk)

        return cls

    def __repr__(self):
        return "<Model: {}>".format(self.__name__)


class Model(with_metaclass(ModelBase, MODEL_BASE_NAME)):
    def __init__(self, *args, **kwargs):
        self.__data__ = {}
        for k, v in kwargs.items():
            setattr(self, k, v)
