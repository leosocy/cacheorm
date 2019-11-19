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
        return "%s,%s" % (self.number, self.phone_type)

    @classmethod
    def de(cls, s):
        elements = s.split(",")
        return cls(str(elements[0]), PhoneType(int(elements[1])))


class User(co.Model):
    id = co.IntegerField(primary_key=True)
    name = co.StringField()
    height = co.FloatField()
    married = co.BooleanField(default=False)
    gender = co.EnumField(Gender, default=Gender.UNKNOWN)
    phones = co.ListField(co.StructField(PhoneNumber.se, PhoneNumber.de), default=[])
    created_at = co.DateTimeTZField(
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc)
    )

    class Meta:
        serializer = None
        backend = None
