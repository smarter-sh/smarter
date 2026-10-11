"""Serializers for converting objects to JSON."""

import datetime

from smarter.lib import json
from smarter.lib.typing import SmarterDictType

__all__ = ["dumps", "serialize_python_dict"]


def datetime_handler(x):
    if isinstance(x, datetime.datetime):
        return x.isoformat()
    raise TypeError("Unknown type")


def dumps(data):
    return json.dumps(data, default=datetime_handler)


def serialize_python_dict(data: SmarterDictType) -> SmarterDictType:
    retval_str = dumps(data)
    return json.loads(retval_str)
