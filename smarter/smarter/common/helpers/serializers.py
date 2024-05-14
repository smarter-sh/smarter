"""Serializers for converting objects to JSON."""

import datetime
import json


__all__ = ["dumps", "serialize_python_dict"]


def datetime_handler(x):
    if isinstance(x, datetime.datetime):
        return x.isoformat()
    raise TypeError("Unknown type")


def dumps(data):
    return json.dumps(data, default=datetime_handler)


def serialize_python_dict(data: dict) -> dict:
    retval_str = dumps(data)
    return json.loads(retval_str)
