import threading

from cacheorm.types import Singleton


class BaseSerializer(object):  # pragma: no cover
    def dumps(self, obj) -> bytes:
        """Serialize ``obj`` to a ``bytes``."""
        raise NotImplementedError

    def loads(self, s):
        """Deserialize ``s`` (a ``bytes``) to a Python object."""
        raise NotImplementedError


class SerializerRegistry(metaclass=Singleton):
    def __init__(self):
        self._serializers = {}
        self._lock = threading.Lock()

    def register(self, unique_name, serializer: BaseSerializer):
        """Register a new serializer.

        If the unique name already exists, it will not be overwritten.

        Arguments:
            unique_name (str): A convenience name for the serialization method.

            serializer (BaseSerializer): Object inherited from BaseSerializer.

        Raises:
            ValueError: If the unique_name already exists.
        """
        with self._lock:
            if unique_name in self._serializers:
                raise ValueError("serializer {} already exists".format(unique_name))
            self._serializers[unique_name] = serializer

    def unregister(self, unique_name):
        """Unregister registered serializer.

        Arguments:
            unique_name (str): Registered serializer name.

        Raises:
            KeyError: If a serializer by that name cannot be found.
        """
        with self._lock:
            try:
                self._serializers.pop(unique_name)
            except KeyError:
                raise KeyError("serializer {} not found".format(unique_name))

    def get_by_name(self, unique_name):
        return self._serializers.get(unique_name, None)


class JSONSerializer(BaseSerializer):
    def __init__(self):
        import json

        self._json = json

    def dumps(self, obj):
        rv = self._json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
        return bytes(rv, encoding="utf-8")

    def loads(self, s):
        return self._json.loads(s)


class MessagePackSerializer(BaseSerializer):
    def __init__(self):
        try:
            import msgpack

            self._msgpack = msgpack
        except ImportError:  # pragma: no cover
            raise ModuleNotFoundError("no msgpack module found.")

    def dumps(self, obj):
        return self._msgpack.dumps(obj, use_bin_type=True)

    def loads(self, s):
        return self._msgpack.loads(s, raw=False)


class PickleSerializer(BaseSerializer):
    def __init__(self):
        import pickle

        self._pickle = pickle

    def dumps(self, obj):
        return self._pickle.dumps(obj)

    def loads(self, s):
        return self._pickle.loads(s)


class ProtobufSerializer(BaseSerializer):
    def __init__(self, descriptor):
        self._descriptor = descriptor

    def dumps(self, obj):
        if isinstance(obj, dict):
            obj = self._descriptor(**obj)
        if isinstance(obj, self._descriptor):
            return self._descriptor.SerializeToString(obj)
        raise TypeError(
            "protocol buffer serializer `dumps` only support Dict/Pb object"
        )

    def loads(self, s):
        return self._descriptor.FromString(s)


registry = SerializerRegistry()


def register_preset_serializers():
    registry.register("json", JSONSerializer())
    registry.register("msgpack", MessagePackSerializer())
    registry.register("pickle", PickleSerializer())
