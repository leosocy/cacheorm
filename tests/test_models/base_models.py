import datetime
import enum
from functools import partial

import cacheorm as co


class Gender(enum.Enum):
    UNKNOWN = 0
    MALE = 1
    FEMALE = 2


class PhoneType(enum.Enum):
    MOBILE = 0
    HOME = 10
    WORD = 20


class PhoneNumber(object):
    def __init__(self, number, phone_type):
        self.number = number
        self.phone_type = phone_type

    def se(self):
        return {"number": self.number, "type": self.phone_type.value}

    @classmethod
    def de(cls, s):
        return cls(str(s["number"]), PhoneType(int(s["type"])))


class User(co.Model):
    id = co.IntegerField(primary_key=True)
    name = co.StringField()
    height = co.DecimalField(auto_round=True)
    married = co.BooleanField(default=False)
    gender = co.EnumField(Gender, default=Gender.UNKNOWN)
    phones = co.ListField(co.StructField(PhoneNumber.se, PhoneNumber.de), default=[])
    created_at = co.DateTimeTZField(
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc)
    )

    class Meta:
        serializer = None
        backend = None
