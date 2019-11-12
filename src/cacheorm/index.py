class IndexFormatter(object):
    def __init__(self, f):
        self.f = f

    @classmethod
    def from_default(cls, model, fields):
        fmt = "m:%s:" % model._meta.name
        for field in fields:
            fmt += field.name + ":%s"
        return cls.from_string_format(fmt)

    @classmethod
    def from_string_format(cls, fmt):
        return cls(lambda *values: fmt % values)

    @classmethod
    def from_callable(cls, f):
        return cls(f)


class Index(object):
    def __init__(self, model, fields, formatter=None):
        self.model = model
        self.fields = fields
        self.defaults = model._meta.defaults
        self.field_names = {field.name for field in fields}
        if isinstance(formatter, str):
            self.formatter = IndexFormatter.from_string_format(formatter)
        elif callable(formatter):
            self.formatter = IndexFormatter.from_callable(formatter)
        else:
            self.formatter = IndexFormatter.from_default(model, fields)

    def make_cache_key(self, model_instance):
        values = []
        for field in self.fields:
            val = model_instance.__data__.get(field.name)
            if val is None:
                try:
                    val = self.defaults[field]
                    if callable(val):
                        val = val()
                except KeyError:
                    raise KeyError(
                        "can't get %s value from instance or default" % field
                    )
                setattr(model_instance, field.name, val)
            values.append(field.cache_value(val))
        return self.formatter.f(*values)


class PrimaryKeyIndex(Index):
    def __init__(self, model, **kwargs):
        super(PrimaryKeyIndex, self).__init__(
            model, model._meta.get_primary_key_fields(), **kwargs
        )


class IndexManager(object):
    def __init__(self, model):
        self.model = model
        self.indexes = []

    def generate_indexes(self):
        primary_key = self.model._meta.primary_key
        self.indexes.append(
            PrimaryKeyIndex(self.model, formatter=primary_key.index_formatter)
        )

    def get_primary_key_index(self):
        return self.indexes[0]


class IndexMatcher(object):
    def __init__(self, model):
        self._model = model
        self._indexes = model._index_manager.indexes

    def match_indexes_for(self, **query):
        query_keys = set(query.keys())
        matched = []
        for index in self._indexes:
            if index.field_names - query_keys:
                continue
            matched.append(index)
        return matched

    def select_index(self, indexes):
        for index in indexes:
            if isinstance(index, PrimaryKeyIndex):
                return index
        return indexes[0]
