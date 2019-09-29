import pytest
from cacheorm.types import Singleton, to_bytes


def test_to_bytes():
    assert b"1" == to_bytes(1)
    assert b"1.23" == to_bytes(1.23)
    assert b"test" == to_bytes("test")
    assert b"\xe5\x93\x88\xe5\x93\x88" == to_bytes("哈哈")
    pickled = b"\x80\x03}q\x00X\x04\x00\x00\x00testq\x01K\x01s."
    assert pickled == to_bytes(pickled)
    with pytest.raises(TypeError):
        to_bytes([1])
    with pytest.raises(TypeError):
        to_bytes({"test": 1})


def test_singleton():
    class Test(metaclass=Singleton):
        __slots__ = ["a"]

        def __init__(self, a):
            self.a = a

    t1 = Test(1)
    t2 = Test(2)
    assert t1 is t2
    assert t2.a == t1.a
