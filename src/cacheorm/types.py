def to_bytes(value):
    if value is None:
        return None
    if isinstance(value, bytes):
        return value
    if isinstance(value, (int, float)):
        value = str(value)
    if isinstance(value, str):
        return value.encode(encoding="utf-8")
    raise TypeError("'%s' object can't covert to bytes" % type(value))


class Singleton(type):
    """A metaclass that creates a Singleton base class when called."""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
