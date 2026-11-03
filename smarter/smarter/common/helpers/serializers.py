"""Serializers for converting objects to JSON."""

import datetime

from smarter.lib import json
from smarter.lib.typing import SmarterDictType

__all__ = ["dumps", "serialize_python_dict"]


def datetime_handler(x):
    """
    Serialize a datetime for :func:`json.dumps`.

    :param x: The value.
    :returns: The ISO 8601 string.
    :raises TypeError: when it is not a datetime.
    """
    if isinstance(x, datetime.datetime):
        return x.isoformat()
    raise TypeError("Unknown type")


def dumps(data):
    """
    Serialize data as json, with datetimes as ISO 8601 strings.

    :param data: The data.
    :returns: The json string.
    """
    return json.dumps(data, default=datetime_handler)


def serialize_python_dict(data: SmarterDictType) -> SmarterDictType:
    """
    Return a json-safe copy of a dict, with datetimes as ISO 8601 strings.

    :param data: The dict.
    :returns: The copy.
    """
    retval_str = dumps(data)
    return json.loads(retval_str)
