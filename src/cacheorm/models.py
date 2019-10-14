import copy
import itertools
from collections import defaultdict

from .fields import Field, FieldAccessor, IntegerField
from .types import with_metaclass


class Index(object):
    def __init__(self, model, fields, formatter=None):
        self.model = model
        self.fields = fields
        self.field_names = {field.name for field in fields}
        if formatter is None:
            formatter = self._default_formatter(model, fields)
        self.formatter = formatter

    def make_cache_key(self, **query):
        missing_keys = self.field_names - set(query.keys())
        if missing_keys:
            raise KeyError("missing index keys %s in query" % missing_keys)
        values = tuple(field.cache_value(query[field.name]) for field in self.fields)
        return self.formatter % values

    @staticmethod
    def _default_formatter(model, fields):
        base = "m:%s:" % model._meta.name
        field_parts = ":".join(itertools.chain(*[(f.name, "%s") for f in fields]))
        return base + field_parts


class PrimaryKeyIndex(Index):
    def __init__(self, model, formatter=None):
        super(PrimaryKeyIndex, self).__init__(
            model, model._meta.get_primary_key_fields(), formatter
        )


class IndexManager(object):
    def __init__(self, model):
        self.model = model
        self.indexes = {}

    def _generate_indexes(self):
        primary_key = self.model._meta.primary_key
        self.indexes[primary_key] = PrimaryKeyIndex(
            self.model, formatter=primary_key.index_formatter
        )

    def get_primary_key_index(self):
        return self.get_index(self.model._meta.primary_key)

    def get_index(self, field):
        return self.indexes.get(field, None)


class Metadata(object):
    def __init__(
        self,
        model,
        backend,
        serializer,
        ttl=None,
        name=None,
        primary_key=None,
        **kwargs
    ):
        self.model = model
        self.backend = backend
        self.serializer = serializer
        self.ttl = ttl
        self.name = name or model.__name__.lower()

        self.fields = {}
        self.defaults = {}
        self.primary_key = primary_key

        for k, v in kwargs.items():
            setattr(self, k, v)
        self._additional_keys = set(kwargs.keys())

    def add_field(self, field_name, field, set_attribute=True):
        field.bind(self.model, field_name, set_attribute)
        self.fields[field.name] = field
        if field.default is not None:
            self.defaults[field] = field.default

    def set_primary_key(self, name, field):
        self.add_field(name, field)
        self.primary_key = field

    def get_primary_key_fields(self):
        return (self.primary_key,)

    def set_backend(self, backend):
        self.backend = backend


class DoesNotExist(Exception):
    pass


MODEL_BASE_NAME = "__metaclass_helper__"


class ModelBase(type):
    inheritable = {"backend", "serializer", "ttl", "primary_key"}

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
                    attrs[k] = copy.deepcopy(v.field)

        cls = super(ModelBase, cls).__new__(cls, name, bases, attrs)
        cls.__data__ = None
        cls._meta = Metadata(cls, **meta_options)
        cls._index_manager = IndexManager(cls)

        fields = []
        for key, value in cls.__dict__.items():
            if isinstance(value, Field):
                if value.primary_key:
                    if pk:
                        raise ValueError("over-determined primary key %s." % name)
                    pk, pk_name = value, key
                else:
                    fields.append((key, value))
        if pk is None:
            if parent_pk is not False:
                pk, pk_name = (
                    (parent_pk, parent_pk.name)
                    if parent_pk is not None
                    else (
                        IntegerField(primary_key=True),
                        "id",
                    )  # TODO(leosocy): AutoField
                )
            else:
                pk = False
        if pk is False:
            raise ValueError("required primary key %s." % name)
        cls._meta.set_primary_key(pk_name, pk)

        for name, field in fields:
            cls._meta.add_field(name, field)

        cls._index_manager._generate_indexes()

        exc_name = "%sDoesNotExist" % cls.__name__
        exc_attrs = {"__module__": cls.__module__}
        cls.DoesNotExist = type(exc_name, (DoesNotExist,), exc_attrs)

        return cls

    def __repr__(cls):
        return "<Model: %s>" % cls.__name__


class Model(with_metaclass(ModelBase, name=MODEL_BASE_NAME)):
    def __init__(self, *args, **kwargs):
        self.__data__ = {}
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __hash__(self):
        return hash((self.__class__, self._pk))

    def __eq__(self, other):
        return (
            self.__class__ == other.__class__
            and self._pk is not None
            and self._pk == other._pk
        )

    def __ne__(self, other):
        return not self == other

    def get_id(self):
        return getattr(self, self._meta.primary_key.name)

    _pk = property(get_id)

    @_pk.setter
    def _pk(self, value):
        setattr(self, self._meta.primary_key.name, value)

    def save(self, force_insert=False):
        # TODO(leosocy): support force_insert
        field_dict = self.__data__.copy()
        self.insert(**field_dict).execute()

    @classmethod
    def insert(cls, **insert):
        return ModelInsert(cls, insert)

    @classmethod
    def insert_many(cls, insert_list):
        """
        :param insert_list:
        [{"name": "Sam"}, Person(name="Amy"), ...]
        :return: ModelInsert object
        """
        return ModelInsert(cls, insert_list)

    @classmethod
    def create(cls, **kwargs):
        inst = cls(**kwargs)
        inst.save(force_insert=True)
        return inst

    @classmethod
    def get(cls, **query):
        index = cls._index_manager.get_primary_key_index()
        cache_key = index.make_cache_key(**query)
        value = cls._meta.backend.get(cache_key)
        if value is None:
            raise cls.DoesNotExist(
                "%s instance matching query does not exist:\nQuery: %s" % (cls, query)
            )
        row = cls._meta.serializer.loads(value)
        converted_row = {}
        for k, v in row.items():
            converted_row[k] = cls._meta.fields[k].python_value(v)
        return cls(**query, **converted_row)

    @classmethod
    def query(cls, **queries):
        pass

    @classmethod
    def query_many(cls, query_list):
        """
        :param query_list: [{"name": "Sam"}, {"name": "Amy"}]
        :return: ModelQuery object
        """
        pass

    @classmethod
    def get_by_id(cls, pk):
        query = {cls._meta.primary_key.name: pk}
        return cls.get(**query)

    @classmethod
    def get_or_none(cls, **query):
        pass

    @classmethod
    def get_or_create(cls, **kwargs):
        pass

    @classmethod
    def update(cls, **update):
        pass

    @classmethod
    def update_many(cls, update_list):
        pass

    @classmethod
    def set_by_id(cls, pk, value):
        pass

    @classmethod
    def delete(cls, **delete):
        pass

    @classmethod
    def delete_many(cls, delete_list):
        pass

    @classmethod
    def delete_by_id(cls, pk):
        pass


class Insert(object):
    # TODO(leosocy): support chunk_size
    def __init__(self, insert_list):
        """
        Insert inserts data list in batches, support different model.

        :param insert_list:
        [Person(name="Sam"), Note(content="foo")]
            or
        [(Person, ({"name": "Sam"}, {"name": "Amy"})), (Note, ({"content": "foo"},))]
        """
        self._insert_list = insert_list

    def execute(self):
        instances = []
        group_by_meta = defaultdict(dict)
        for model, index, payload in self._generate_insert(self._insert_list):
            meta = model._meta
            primary_key_index = model._index_manager.get_primary_key_index()
            instances.append(model(**index, **payload))
            cache_key = primary_key_index.make_cache_key(**index)
            group_by_meta[(meta.backend, meta.ttl)][cache_key] = meta.serializer.dumps(
                payload
            )
        for (backend, ttl), mapping in group_by_meta.items():
            backend.set_many(mapping, ttl=ttl)
        return instances

    @staticmethod
    def _parse_model_rows(insert):
        if isinstance(insert, Model):
            model = type(insert)
            rows = (insert.__data__,)
        elif isinstance(insert, tuple) and isinstance(insert[0], ModelBase):
            model = insert[0]
            rows = insert[1]
        else:
            raise TypeError("unsupported insert type")
        return model, rows

    @staticmethod
    def _generate_insert(insert_list):
        for insert in insert_list:
            model, rows = Insert._parse_model_rows(insert)
            fields_converters = [
                (field, field.cache_value) for field in model._meta.fields.values()
            ]
            defaults = model._meta.defaults
            primary_key_fields = model._meta.get_primary_key_fields()
            for row in rows:
                payload = {}
                index = {}
                for field, converter in fields_converters:
                    try:
                        val = converter(row[field.name])
                    except KeyError:
                        if field in defaults:
                            # TODO(leosocy): support callable default
                            val = defaults[field]
                        elif field.null:
                            continue
                        else:
                            raise ValueError("missing value for '%s'." % field)
                    if field in primary_key_fields:
                        index[field.name] = val
                    else:
                        payload[field.name] = val
                yield model, index, payload


class Query(object):
    pass


class ModelInsert(Insert):
    def __init__(self, model, insert):
        self._single = False
        insert_list = []
        if isinstance(insert, dict):
            self._single = True
            insert_list.append((model, (insert,)))
        elif isinstance(insert, (list, tuple)):
            for ele in insert:
                if isinstance(ele, dict):
                    insert_list.append((model, (ele,)))
                elif isinstance(ele, model):
                    insert_list.append(ele)
        else:
            raise TypeError("unsupported insert type")
        super(ModelInsert, self).__init__(insert_list)

    def execute(self):
        instances = super(ModelInsert, self).execute()
        return instances[0] if self._single else instances


class ModelQuery(Query):
    pass
