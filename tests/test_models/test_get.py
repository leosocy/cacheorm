import time

import pytest


def test_get_when_cache_expired(person_model):
    class WrappedPerson(person_model):
        class Meta:
            ttl = 1

    sam = WrappedPerson.create(name="Sam", height=178.6)
    got_sam = WrappedPerson.get_by_id("Sam")
    assert got_sam == sam
    time.sleep(1.1)
    with pytest.raises(WrappedPerson.DoesNotExist):
        WrappedPerson.get_by_id("Sam")
