import copy
from collections import defaultdict

from .fields import Field, FieldAccessor, IntegerField
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
        # TODO(leosocy): support force_insert
        field_dict = self.__data__.copy()
        if self._pk is not None and not force_insert:
            inst = self.update(**field_dict).execute()
        else:
            inst = self.insert(**field_dict).execute()
        return inst is not None

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
        query = {cls._meta.primary_key.name: pk}
        return cls.get(**query)

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
        update.update({cls._meta.primary_key.name: pk})
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
        :return: affected_rows
        :rtype: int
        """
        pass

    @classmethod
    def delete_many(cls, *delete_list):
        """
        根据一批主键fields对应的values去backend删除。
        :param delete_list: 同query_many
        :return: affected_rows
        :rtype: int
        """

    @classmethod
    def delete_by_id(cls, pk):
        pass


class _InputParser(object):
    """
    input should be a tuple or list, format like:
    [
        (Person, [{"name": "Sam"}, {"name": "Amy"}]),
        Note(content="foo"), Note(content="bar"),
    ]
    """

    def __init__(self, only_index=False, skip_key_error=False):
        self._only_index = only_index
        self._skip_key_error = skip_key_error

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

    def parse(self, inputs):  # noqa
        for input in inputs:
            model, rows = self._parse_to_model_rows(input)
            matcher = IndexMatcher(model)
            defaults = model._meta.defaults
            for row in rows:
                indexes = matcher.match_indexes_for(**row)
                if not indexes:
                    raise ValueError("can't match any index for row %s" % row)
                index = matcher.select_index(indexes)
                fields = (
                    index.fields if self._only_index else model._meta.fields.values()
                )
                payload_dict = {}
                index_dict = {}
                for field in fields:
                    try:
                        val = field.cache_value(row[field.name])
                    except KeyError:
                        if self._skip_key_error:
                            continue
                        if field in defaults:
                            # TODO(leosocy): support callable default
                            val = defaults[field]
                        elif field.null:
                            continue
                        else:
                            raise ValueError("missing value for '%s'." % field)
                    if field in index.fields:
                        index_dict[field.name] = val
                    else:
                        payload_dict[field.name] = val
                yield model, index_dict, payload_dict


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
        for model, index, payload in _InputParser().parse(self._insert_list):
            meta = model._meta
            primary_key_index = model._index_manager.get_primary_key_index()
            cache_key = primary_key_index.make_cache_key(**index)
            group_by_meta[(meta.backend, meta.ttl)][cache_key] = meta.serializer.dumps(
                payload
            )
            instances.append(model(**index, **payload))
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
        for model, index, _ in _InputParser(only_index=True).parse(self._query_list):
            group_by_backend[model._meta.backend].append((model, index))
        for backend, pairs in group_by_backend.items():
            cache_keys = []
            for model, index in pairs:
                primary_key_index = model._index_manager.get_primary_key_index()
                cache_key = primary_key_index.make_cache_key(**index)
                cache_keys.append(cache_key)
            for val, (model, index) in zip(backend.get_many(*cache_keys), pairs):
                if val is not None:
                    val = model._meta.serializer.loads(val)
                    converted_row = {}
                    for k, v in val.items():
                        converted_row[k] = model._meta.fields[k].python_value(v)
                    instances.append(model(**index, **converted_row))
                else:
                    instances.append(None)
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
        for (model, index, payload), original_instance in zip(
            _InputParser(skip_key_error=True).parse(self._update_list),
            original_instances,
        ):
            if original_instance is None:
                instances.append(None)
                continue
            meta = model._meta
            primary_key_index = model._index_manager.get_primary_key_index()
            cache_key = primary_key_index.make_cache_key(**index)
            for k, v in original_instance.__data__.items():
                if model._meta.fields[k] not in model._meta.get_primary_key_fields():
                    payload.update({k: v})
            group_by_meta[(meta.backend, meta.ttl)][cache_key] = meta.serializer.dumps(
                payload
            )
            instances.append(model(**index, **payload))
        for (backend, ttl), mapping in group_by_meta.items():
            backend.replace_many(mapping, ttl=ttl)
        return instances


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


# NOTE(leosocy):
#  1. IndexMatcher 根据query，生成所有匹配的indexes，交给调用者决定如何使用索引。
#  2. Where 根据index及传入的query，分离index string以及剩余的payload。其中index需要包括convert(cache_value)逻辑。
#  3. Payloader to_cache, from_cache。
#   - 根据传入的query，调用cache_value生成需要保存到cache backend的值。
#   - 根据传入的bytes，调用python_value生成dict。
