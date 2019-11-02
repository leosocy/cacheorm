import itertools


class IndexFormatter(object):
    def __init__(self, f):
        self._f = f

    def make_cache_key(self, **query):
        pass

    @classmethod
    def from_string_format(cls, fmt):
        pass

    @classmethod
    def from_callable(cls, f):
        pass

    @classmethod
    def from_default(cls, model, fields):
        pass


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
