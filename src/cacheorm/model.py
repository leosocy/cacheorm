import copy
from collections import defaultdict

from .fields import CompositeKey, Field, FieldAccessor, IntegerField
from .index import IndexManager, IndexMatcher
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
        elif isinstance(pk, CompositeKey):
            pk_name = "__composite_key__"
        if pk is False:
            raise ValueError("required primary key %s." % name)
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
        {"name": "Sam"}, Person(name="Amy"), ...
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


class IndexDumper(object):
    def dump(self):
        pass

    def original(self):
        pass


class RowSplitterFactory(object):
    _splitters = {}

    @staticmethod
    def create(model, index):
        cached = RowSplitterFactory._splitters.get((model, index), None)
        if cached is not None:
            return cached
        splitter = RowSplitter(model, index)
        RowSplitterFactory._splitters[(model, index)] = splitter
        return splitter


class RowSplitter(object):
    def __init__(self, model, index):
        self._model = model
        self._index = index
        self._all_fields = model._meta.fields.values()
        self._index_fields = index.fields
        self._defaults = model._meta.defaults

    def split(self, row, skip_payload=False, skip_key_error=False):
        fields = self._index_fields if skip_payload else self._all_fields
        index = {}
        payload = {}
        for field in fields:
            try:
                val = field.cache_value(row[field.name])
            except KeyError:
                if skip_key_error:
                    continue
                if field in self._defaults:
                    val = self._defaults[field]
                    if callable(val):
                        val = val()
                elif field.null:
                    continue
                else:
                    raise ValueError("missing value for '%s'." % field)
            if field in self._index_fields:
                index[field.name] = val
            else:
                payload[field.name] = val
        return index, payload


class _RowScanner(object):
    """
    input should be a tuple or list, format like:
    [
        (Person, [{"name": "Sam"}, {"name": "Amy"}]),
        Note(content="foo"), Note(content="bar"),
    ]
    """

    @staticmethod
    def _parse_to_model_rows(input):
        if isinstance(input, Model):
            model = type(input)
            rows = [input.__data__]
        elif (
            isinstance(input, tuple)
            and isinstance(input[0], ModelBase)
            and isinstance(input[1], (tuple, list))
        ):
            model = input[0]
            rows = input[1]
        else:
            raise TypeError("unsupported input format")
        return model, rows

    @staticmethod
    def scan(inputs):
        for input in inputs:
            model, rows = _RowScanner._parse_to_model_rows(input)
            for row in rows:
                yield model, row


class Insert(object):
    # TODO(leosocy): support chunk_size
    def __init__(self, insert_list):
        """
        Insert inserts data list in batches, support different model.

        :param insert_list:
        [(Person, ({"name": "Sam"}, {"name": "Amy"})), Note(content="foo")]
        """
        self._insert_list = insert_list

    def execute(self):
        instances = []
        group_by_meta = defaultdict(dict)
        for model, row in _RowScanner.scan(self._insert_list):
            row = model(**row).__data__.copy()
            matcher = IndexMatcher(model)
            indexes = matcher.match_indexes_for(**row)
            if not indexes:
                index = model._index_manager.get_primary_key_index()
            else:
                index = matcher.select_index(indexes)
            splitter = RowSplitterFactory.create(model, index)
            index_data, payload_data = splitter.split(row)
            meta = model._meta
            cache_key = index.make_cache_key(**index_data)
            group_by_meta[(meta.backend, meta.ttl)][cache_key] = meta.serializer.dumps(
                payload_data
            )
            instances.append(model(**index_data, **payload_data))
        for (backend, ttl), mapping in group_by_meta.items():
            backend.set_many(mapping, ttl=ttl)
        return instances


class Query(object):
    def __init__(self, query_list):
        """
        :param query_list:
        [(Person, ({"name": "Sam"}, {"name": "Amy"}),
         (Note, ({"id": 1},))]
        """
        self._query_list = query_list

    def execute(self):
        instances = []
        group_by_backend = defaultdict(list)
        for model, row in _RowScanner.scan(self._query_list):
            group_by_backend[model._meta.backend].append((model, row))
        for backend, pairs in group_by_backend.items():
            cache_keys = []
            for model, row in pairs:
                row = model(**row).__data__.copy()
                matcher = IndexMatcher(model)
                indexes = matcher.match_indexes_for(**row)
                if not indexes:
                    raise ValueError("can't match any index for row %s" % row)
                index = matcher.select_index(indexes)
                splitter = RowSplitterFactory.create(model, index)
                index_data, _ = splitter.split(row, skip_payload=True)
                cache_key = index.make_cache_key(**index_data)
                cache_keys.append(cache_key)
                instances.append(model(**index_data))
            for val, (idx, inst) in zip(
                backend.get_many(*cache_keys), enumerate(instances)
            ):
                if val is not None:
                    val = inst._meta.serializer.loads(val)
                    for k, v in val.items():
                        setattr(inst, k, model._meta.fields[k].python_value(v))
                else:
                    instances[idx] = None
        return instances


class Update(object):
    def __init__(self, update_list):
        """
        :param update_list:
        [(Person, ({"name": "Sam", "height": 180}, {"name": "Amy", "married": True})),
         Note(id=1, content="foo", Person(name="Bob", email="bob@outlook.com")]
        """
        self._update_list = update_list

    def execute(self):
        original_instances = Query(self._update_list).execute()
        instances = []
        group_by_meta = defaultdict(dict)
        for (model, row), original_instance in zip(
            _RowScanner.scan(self._update_list), original_instances
        ):
            if original_instance is None:
                instances.append(None)
                continue
            row = model(**row).__data__.copy()
            matcher = IndexMatcher(model)
            indexes = matcher.match_indexes_for(**row)
            if not indexes:
                raise ValueError("can't match any index for row %s" % row)
            index = matcher.select_index(indexes)
            for k, v in original_instance.__data__.items():
                if k not in index.field_names and k not in row:
                    row.update({k: v})
            splitter = RowSplitterFactory.create(model, index)
            index_data, payload_data = splitter.split(row)
            meta = model._meta
            cache_key = index.make_cache_key(**index_data)
            group_by_meta[(meta.backend, meta.ttl)][cache_key] = meta.serializer.dumps(
                payload_data
            )
            instances.append(model(**index_data, **payload_data))
        for (backend, ttl), mapping in group_by_meta.items():
            backend.set_many(mapping, ttl=ttl)
        return instances


class Delete(object):
    def __init__(self, delete_list):
        self._delete_list = delete_list

    def execute(self):
        group_by_backend = defaultdict(list)
        for model, row in _RowScanner.scan(self._delete_list):
            row = model(**row).__data__.copy()
            matcher = IndexMatcher(model)
            indexes = matcher.match_indexes_for(**row)
            if not indexes:
                raise ValueError("can't match any index for row %s" % row)
            index = matcher.select_index(indexes)
            splitter = RowSplitterFactory.create(model, index)
            index_data, _ = splitter.split(row, skip_payload=True)
            cache_key = index.make_cache_key(**index_data)
            group_by_backend[model._meta.backend].append(cache_key)
        return all(
            backend.delete_many(*cache_keys)
            for backend, cache_keys in group_by_backend.items()
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


# NOTE(leosocy):
#  1. IndexMatcher 根据query，生成所有匹配的indexes，交给调用者决定如何使用索引。
#  2. Where 根据index及传入的query，分离index string以及剩余的payload。其中index需要包括convert(cache_value)逻辑。
#  3. Payloader to_cache, from_cache。
#   - 根据传入的query，调用cache_value生成需要保存到cache backend的值。
#   - 根据传入的bytes，调用python_value生成dict。
