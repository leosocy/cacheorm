import copy
import uuid
from collections import defaultdict

from .fields import CompositeKey, Field, FieldAccessor, UUIDField
from .index import IndexManager
from .types import with_metaclass


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
        self.composite_key = False

        for k, v in kwargs.items():
            setattr(self, k, v)
        self._additional_keys = set(kwargs.keys())

    def add_field(self, field_name, field, set_attribute=True):
        field.bind(self.model, field_name, set_attribute)
        if not isinstance(field, CompositeKey):
            self.fields[field.name] = field
            if field.default is not None:
                self.defaults[field] = field.default

    def set_primary_key(self, name, field):
        self.composite_key = isinstance(field, CompositeKey)
        self.add_field(name, field)
        self.primary_key = field

    def get_primary_key_fields(self):
        if self.composite_key:
            return tuple(
                self.fields[field_name] for field_name in self.primary_key.field_names
            )
        return (self.primary_key,)


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
        cls.__data__ = cls.__rel__ = None
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
            pk, pk_name = (
                (parent_pk, parent_pk.name)
                if parent_pk is not None
                else (UUIDField(primary_key=True, default=uuid.uuid4), "id")
            )
        elif isinstance(pk, CompositeKey):
            pk_name = "__composite_key__"

        cls._meta.set_primary_key(pk_name, pk)
        for name, field in fields:
            cls._meta.add_field(name, field)
        cls._index_manager.generate_indexes()

        exc_name = "%sDoesNotExist" % cls.__name__
        exc_attrs = {"__module__": cls.__module__}
        cls.DoesNotExist = type(exc_name, (DoesNotExist,), exc_attrs)

        return cls

    def __repr__(cls):
        return "<Model: %s>" % cls.__name__


class Model(with_metaclass(ModelBase, name=MODEL_BASE_NAME)):
    def __init__(self, *args, **kwargs):
        self.__data__ = {}
        self.__rel__ = {}
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
        return not self.__eq__(other)

    def get_id(self):
        return getattr(self, self._meta.primary_key.name, None)

    _pk = property(get_id)

    @_pk.setter
    def _pk(self, value):
        setattr(self, self._meta.primary_key.name, value)

    def save(self, force_insert=False):
        """
        保存self到backend。
        :param force_insert: 仅当self.pk有值时有效，如果为False则为update，否则为insert
        :return: 是否保存成功。
        :rtype: boolean
        :raise: ValueError: 缺少构造Model字段所需的值
        """
        field_dict = self.__data__.copy()
        if self._pk is not None and not force_insert:
            inst = self.update(**field_dict).execute()
        else:
            inst = self.insert(**field_dict).execute()
            if inst is not None:
                self.__data__ = copy.deepcopy(inst.__data__)
        return inst is not None

    def delete_instance(self):
        return self.delete(**self._meta.primary_key.__key__(self._pk)).execute()

    @classmethod
    def insert(cls, **insert):
        """
        无条件插入数据到backend，如果记录已经存在，则覆盖旧值。
        :param insert: fields对应的name和value，例如{"name": "Sam"}
        :return: 如果成功插入则返回Model对象，否则为None
        :rtype: ModelObject
        """
        return ModelInsert(cls, insert)

    @classmethod
    def insert_many(cls, *insert_list):
        """
        无条件插入一批数据到backend，
        :param insert_list: a list/tuple, contains element like
        {"name": "Sam"}, user(name="Amy"), ...
        :return: [ModelObject, ModelObject, ...]
        :rtype: list
        """
        return ModelInsert(cls, insert_list)

    @classmethod
    def create(cls, **kwargs):
        inst = cls(**kwargs)
        inst.save(force_insert=True)
        return inst

    @classmethod
    def query(cls, **query):
        """
        根据主键fields对应的values去backend查找。
        :param query: primary key fields对应的name和value，例如{"name": "Sam"}
        :return: 如果找到则返回Model对象，否则为None
        :rtype: ModelObject
        :raise: ValueError: query中缺少构造主键cache_key的所需的键值
        """
        return ModelQuery(cls, query)

    @classmethod
    def query_many(cls, *query_list):
        """
        根据一批主键fields对应的values去backend查找。
        :param query_list: a list/tuple, contains element like
        [{"name": "Sam"}, {"name": "Amy"}, ...]
        :return: [ModelObject, None, ...]
        :rtype: list
        :raise: ValueError: query中缺少构造主键cache_key的所需的键值
        """
        return ModelQuery(cls, query_list)

    @classmethod
    def get(cls, **query):
        """
        根据主键fields对应的values去backend查找。
        :param query: primary key fields对应的name和value，例如{"name": "Sam"}
        :return: 如果找到则返回Model对象，否则抛错
        :rtype: ModelObject
        :raises:
        ValueError: query中缺少构造主键cache_key的所需的键值
        DoesNotExist: 记录不存在
        """
        inst = cls.query(**query).execute()
        if inst is None:
            raise cls.DoesNotExist(
                "%s instance matching query does not exist:\nQuery: %s" % (cls, query)
            )
        return inst

    @classmethod
    def get_by_id(cls, pk):
        return cls.get(**cls._meta.primary_key.__key__(pk))

    @classmethod
    def get_or_none(cls, **query):
        try:
            return cls.get(**query)
        except DoesNotExist:
            return None

    @classmethod
    def get_or_create(cls, **kwargs):
        try:
            return cls.get(**kwargs), False
        except DoesNotExist:
            return cls.create(**kwargs), True

    @classmethod
    def update(cls, **update):
        """
        覆盖backend中主键{fields: values}对应的记录，该记录原有的TTL将被清除。
        :param update: 同insert
        :return: 覆盖成功则返回ModelObject；如果原记录不存在否则返回None
        :rtype: ModelObject
        """
        return ModelUpdate(cls, update)

    @classmethod
    def update_many(cls, *update_list):
        """
        批量覆盖backend中主键{fields: values}对应的记录。
        :param update_list: 一个list/tuple，每一个元素都是一个dict，
               其中包含了要更新的主键值以及其他字段值
        :return: [ModelObject, None, ...]
        :rtype: list
        """
        return ModelUpdate(cls, update_list)

    @classmethod
    def set_by_id(cls, pk, value):
        update = copy.deepcopy(value)
        update.update(cls._meta.primary_key.__key__(pk))
        inst = ModelUpdate(cls, update).execute()
        if inst is None:
            raise cls.DoesNotExist(
                "%s instance matching query does not exist:\nQuery: %s" % (cls, pk)
            )
        return inst

    @classmethod
    def delete(cls, **delete):
        """
        根据主键fields对应的values去backend删除。
        :param delete: 同query
        :return: 删除成功则返回True，否则如果记录不存在则为False
        :rtype: bool
        """
        return ModelDelete(cls, delete)

    @classmethod
    def delete_many(cls, *delete_list):
        """
        根据一批主键fields对应的values去backend删除。
        :param delete_list: 同query_many
        :return: 全部删除成功则返回True，否则为False
        :rtype: bool
        """
        return ModelDelete(cls, delete_list)

    @classmethod
    def delete_by_id(cls, pk):
        deleted = ModelDelete(cls, cls._meta.primary_key.__key__(pk)).execute()
        if deleted is False:
            raise cls.DoesNotExist(
                "%s instance matching query does not exist:\nQuery: %s" % (cls, pk)
            )
        return deleted


class _RowScanner(object):
    """
    input should be a tuple or list, format like:
    [
        (user, [{"name": "Sam"}, {"name": "Amy"}]),
        Note(content="foo"), Note(content="bar"),
    ]
    """

    @staticmethod
    def _parse_to_model_rows(ele):
        if isinstance(ele, Model):
            model = type(ele)
            rows = [ele.__data__]
        elif (
            isinstance(ele, tuple)
            and isinstance(ele[0], ModelBase)
            and isinstance(ele[1], (tuple, list))
        ):
            model = ele[0]
            rows = ele[1]
        else:
            raise TypeError("unsupported element format")
        return model, rows

    @staticmethod
    def scan(elements):
        for ele in elements:
            model, rows = _RowScanner._parse_to_model_rows(ele)
            for row in rows:
                yield model, row


class CacheBuilder(object):
    def __init__(self, model, row=None, instance=None):
        self.model = model
        if instance is None:
            instance = model(**(row or {}))
        self._instance = instance
        self._index = model._index_manager.get_primary_key_index()

    def set_instance(self, instance):
        self._instance = instance

    def get_instance(self):
        return self._instance

    def _get_field_value(self, field, set_attribute=True, nullable=False):
        val = self._instance.__data__.get(field.name)
        if val is not None:
            return val
        if field in self.model._meta.defaults:
            val = self.model._meta.defaults[field]
            if callable(val):
                val = val()
            if set_attribute:
                setattr(self._instance, field.name, val)
            return val
        elif nullable and field.null:
            return None
        else:
            raise ValueError("missing value for %s" % field)

    def build_key(self):
        values = []
        for field in self._index.fields:
            value = self._get_field_value(field)
            values.append(field.cache_value(value))
        return self._index.formatter.f(*values)

    def build_payload(self):
        payload = {}
        for name, field in self.model._meta.fields.items():
            if name in self._index.field_names:
                continue
            value = self._get_field_value(field, nullable=True)
            if value is not None:
                payload.update({name: field.cache_value(value)})
        return self.model._meta.serializer.dumps(payload)

    def load_payload(self, s, on_conflict_update=True):
        payload = self.model._meta.serializer.loads(s)
        for name, field in self.model._meta.fields.items():
            if name in self._index.field_names:
                continue
            if name in payload:
                if self._instance.__data__.get(name) is None or on_conflict_update:
                    setattr(self._instance, name, field.python_value(payload[name]))
            # TODO: 如果使用Protobuf serializer，有可能字段值是不是null，但是payload中没有对应的值
            #  因为Protobuf不会存储字段的默认值，例如int型值为0时。


class Insert(object):
    # TODO(leosocy): support chunk_size
    def __init__(self, insert_list):
        """
        Insert inserts data list in batches, support different model.

        :param insert_list:
        [(user, ({"name": "Sam"}, {"name": "Amy"})), Note(content="foo")]
        """
        self._insert_list = insert_list

    def execute(self):
        builders = []
        group_by_meta = defaultdict(list)
        for model, row in _RowScanner.scan(self._insert_list):
            builder = CacheBuilder(model, row=row)
            builders.append(builder)
            meta = model._meta
            group_by_meta[(meta.backend, meta.ttl)].append(builder)
        if len(group_by_meta) == 1:
            backend, ttl = list(group_by_meta.keys())[0]
            builder = list(group_by_meta.values())[0][0]
            backend.set(builder.build_key(), builder.build_payload(), ttl=ttl)
        for (backend, ttl), bs in group_by_meta.items():
            if len(bs) == 1:
                # faster way when only one key/value to set
                b = bs[0]
                backend.set(b.build_key(), b.build_payload(), ttl=ttl)
            else:
                backend.set_many(
                    {b.build_key(): b.build_payload() for b in bs}, ttl=ttl
                )
        return [builder.get_instance() for builder in builders]


class Query(object):
    def __init__(self, query_list):
        """
        :param query_list:
        [(user, ({"name": "Sam"}, {"name": "Amy"}),
         (Note, ({"id": 1},))]
        """
        self._query_list = query_list

    def execute(self):
        builders = []
        group_by_backend = defaultdict(list)
        for model, row in _RowScanner.scan(self._query_list):
            builder = CacheBuilder(model, row=row)
            builders.append(builder)
            group_by_backend[model._meta.backend].append(builder)
        for backend, bs in group_by_backend.items():
            cache_keys = [b.build_key() for b in bs]
            payloads = backend.get_many(*cache_keys)
            for payload, b in zip(payloads, bs):
                if payload is None:
                    b.set_instance(None)
                    continue
                b.load_payload(payload)
        return [builder.get_instance() for builder in builders]


class Update(object):
    def __init__(self, update_list):
        """
        :param update_list:
        [(user, ({"name": "Sam", "height": 180}, {"name": "Amy", "married": True})),
         Note(id=1, content="foo", user(name="Bob", email="bob@outlook.com")]
        """
        self._update_list = update_list

    def execute(self):
        builders = []
        group_by_backend = defaultdict(list)
        group_by_meta = defaultdict(list)
        for model, row in _RowScanner.scan(self._update_list):
            builder = CacheBuilder(model, row=row)
            builders.append(builder)
            meta = model._meta
            group_by_backend[meta.backend].append(builder)
            group_by_meta[(meta.backend, meta.ttl)].append(builder)
        for backend, bs in group_by_backend.items():
            cache_keys = [b.build_key() for b in bs]
            payloads = backend.get_many(*cache_keys)
            for payload, b in zip(payloads, bs):
                if payload is None:
                    b.set_instance(None)
                    continue
                b.load_payload(payload, on_conflict_update=False)
        for (backend, ttl), bs in group_by_meta.items():
            mapping = {}
            for b in bs:
                if b.get_instance() is not None:
                    mapping[b.build_key()] = b.build_payload()
            if len(mapping) == 1:
                backend.set(*mapping.popitem(), ttl=ttl)
            elif len(mapping) > 1:
                backend.set_many(mapping, ttl=ttl)
        return [builder.get_instance() for builder in builders]


class Delete(object):
    def __init__(self, delete_list):
        self._delete_list = delete_list

    def execute(self):
        group_by_backend = defaultdict(list)
        for model, row in _RowScanner.scan(self._delete_list):
            builder = CacheBuilder(model, row=row)
            group_by_backend[model._meta.backend].append(builder)
        return all(
            backend.delete_many(*[b.build_key() for b in bs])
            for backend, bs in group_by_backend.items()
        )


class _ModelOpHelper(object):
    def __init__(self, model, rows):
        self._single = False
        row_list = []
        if isinstance(rows, dict):
            self._single = True
            row_list.append((model, (rows,)))
        elif isinstance(rows, (list, tuple)):
            for row in rows:
                if isinstance(row, dict):
                    row_list.append((model, (row,)))
                elif isinstance(row, model):
                    row_list.append(row)
        else:
            raise TypeError("unsupported rows type")
        super(_ModelOpHelper, self).__init__(row_list)

    def execute(self):
        instances = super(_ModelOpHelper, self).execute()
        return instances[0] if self._single else instances


class ModelInsert(_ModelOpHelper, Insert):
    pass


class ModelQuery(_ModelOpHelper, Query):
    pass


class ModelUpdate(_ModelOpHelper, Update):
    pass


class ModelDelete(_ModelOpHelper, Delete):
    def execute(self):
        return super(_ModelOpHelper, self).execute()
