import copy

from .fields import Field, FieldAccessor
from .types import with_metaclass


class CacheKeyManager(object):
    def __init__(self, formatter=None):
        self.formatter = formatter


class Metadata(object):
    def __init__(self, model, backend, serializer, primary_key=None, **kwargs):
        self.model = model
        self.backend = backend
        self.serializer = serializer
        self.name = model.__name__.lower()
        self.primary_key = primary_key
        for k, v in kwargs.items():
            setattr(self, k, v)
        self._additional_keys = set(kwargs.keys())

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

    def __new__(cls, name, bases, attrs):  # noqa: C901
        if name == MODEL_BASE_NAME or bases[0].__name__ == MODEL_BASE_NAME:
            return super(ModelBase, cls).__new__(cls, name, bases, attrs)

        meta_options = {}
        meta = attrs.pop("Meta", None)
        if meta:
            for k, v in meta.__dict__.items():
                if not k.startswith("_"):
                    meta_options[k] = v

        pk = getattr(meta, "primary_key", None)
        pk_name = parent_pk = None

        # Inherit any field descriptors by deep copying the underlying field
        # into the attrs of the new model, additionally see if the bases define
        # inheritable model options and swipe them.
        for b in bases:
            if not hasattr(b, "_meta"):
                continue
            base_meta = b._meta
            if parent_pk is None:
                parent_pk = copy.deepcopy(base_meta.primary_key)
            all_inheritable = cls.inheritable | base_meta._additional_keys
            for k, v in base_meta.__dict__.items():
                if k in all_inheritable and k not in meta_options:
                    meta_options[k] = v
            for k, v in b.__dict__.items():
                if k in attrs:
                    continue
                if isinstance(v, FieldAccessor) and not v.field.primary_key:
                    attrs[k] = copy.deepcopy(v)

        cache_key_options = meta_options.pop("cache_key_options", {})

        cls = super(ModelBase, cls).__new__(cls, name, bases, attrs)
        cls.__data__ = None
        cls._meta = Metadata(cls, **meta_options)
        cls._cache_key = CacheKeyManager(**cache_key_options)

        fields = []
        for key, value in cls.__dict__.items():
            if isinstance(value, Field):
                if value.primary_key:
                    if pk:
                        raise ValueError("over-determined primary key %s." % name)
                    pk, pk_name = value, key
                else:
                    fields.append((key, value))
        if pk is None and parent_pk:
            pk, pk_name = parent_pk, parent_pk.name
        if pk is False:
            raise ValueError("required primary key %s." % name)
        cls._meta.set_primary_key(pk_name, pk)

        for name, field in fields:
            cls._meta.add_field(name, field)

        return cls


class Model(with_metaclass(ModelBase, name=MODEL_BASE_NAME)):
    def __init__(self, *args, **kwargs):
        self.__data__ = {}
        for k, v in kwargs.items():
            setattr(self, k, v)

    def save(self, force_insert=False):
        pass

    @classmethod
    def create(cls, **query):
        inst = cls(**query)
        inst.save(force_insert=True)
        return inst

    @classmethod
    def get(cls, **query):
        pass

    @classmethod
    def get_by_id(cls, pk):
        return cls.get(id=pk)
