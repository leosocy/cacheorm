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
