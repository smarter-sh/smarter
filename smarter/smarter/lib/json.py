"""
Overridden JSON utilities. The effective modifications are
- Use SmarterJSONEncoder as the default encoder
- Standardize indentation to 2 characters
- Use str as the default for non-serializable objects
- Support for additional types in SmarterJSONEncoder:
  - datetime.datetime, datetime.date, datetime.time, datetime.timedelta
  - decimal.Decimal
  - uuid.UUID
  - Django TaggableManager
"""

import datetime
import decimal
import json
import uuid

# pylint: disable=unused-import
from json import (  # unmodified re-export
    JSONDecodeError,
    JSONDecoder,
    load,
    loads,
)


class Promise:
    """
    Base class for the proxy class created in the closure of the lazy function.
    It's used to recognize promises in code.
    """


def _get_duration_components(duration):
    days = duration.days
    seconds = duration.seconds
    microseconds = duration.microseconds

    minutes = seconds // 60
    seconds %= 60

    hours = minutes // 60
    minutes %= 60

    return days, hours, minutes, seconds, microseconds


def is_aware(value):
    """
    Determine if a given datetime.datetime is aware.

    The concept is defined in Python's docs:
    https://docs.python.org/library/datetime.html#datetime.tzinfo

    Assuming value.tzinfo is either None or a proper datetime.tzinfo,
    value.utcoffset() implements the appropriate logic.
    """
    return value.utcoffset() is not None


def duration_iso_string(duration):
    if duration < datetime.timedelta(0):
        sign = "-"
        duration *= -1
    else:
        sign = ""

    days, hours, minutes, seconds, microseconds = _get_duration_components(duration)
    ms = ".{:06d}".format(microseconds) if microseconds else ""
    return "{}P{}DT{:02d}H{:02d}M{:02d}{}S".format(sign, days, hours, minutes, seconds, ms)


class SmarterJSONEncoder(json.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode odd types like
     - date/time
     - decimal
     - UUIDs
     - TaggableManager
    """

    def default(self, o):
        # TaggableManager support (import inside to avoid startup issues)
        # most common cases. pass back the super().default(o)
        if isinstance(o, (str, int, float, type(None), bool)):
            return super().default(o)
        # See "Date Time String Format" in the ECMA-262 specification.
        elif isinstance(o, datetime.datetime):
            r = o.isoformat()
            if o.microsecond:
                r = r[:23] + r[26:]
            if r.endswith("+00:00"):
                r = r.removesuffix("+00:00") + "Z"
            return r
        elif isinstance(o, datetime.date):
            return o.isoformat()
        elif isinstance(o, datetime.time):
            if is_aware(o):
                raise ValueError("JSON can't represent timezone-aware times.")
            r = o.isoformat()
            if o.microsecond:
                r = r[:12]
            return r
        elif isinstance(o, datetime.timedelta):
            return duration_iso_string(o)
        elif isinstance(o, (decimal.Decimal, uuid.UUID, Promise)):
            return str(o)
        else:
            # Handle GenericRelatedObjectManager by type name and module (avoids import timing issues)
            if (
                type(o).__name__ == "GenericRelatedObjectManager"
                and getattr(type(o), "__module__", None) == "django.contrib.contenttypes.fields"
            ):
                return list(o.all())

            # Handle TaggableManager
            try:
                # pylint: disable=C0415
                from taggit.managers import TaggableManager

                _TaggableManager = getattr(
                    __import__("taggit.managers", fromlist=["_TaggableManager"]), "_TaggableManager", None
                )
                taggable_types = (TaggableManager,)
                if _TaggableManager:
                    taggable_types += (_TaggableManager,)
                if isinstance(o, taggable_types):
                    return list(o.all().values_list("name", flat=True))
            except ImportError:
                pass

            return super().default(o)


def dumps(
    obj,
    *,
    skipkeys=False,
    ensure_ascii=True,
    check_circular=True,
    allow_nan=True,
    cls=None,
    indent=None,
    separators=None,
    default=None,
    sort_keys=False,
    **kw,
):
    """
    JSON dump with
    - SmarterJSONEncoder as default encoder
    - indent of 2
    - default of str
    """

    return json.dumps(
        obj,
        skipkeys=skipkeys,
        ensure_ascii=ensure_ascii,
        check_circular=check_circular,
        allow_nan=allow_nan,
        cls=cls or SmarterJSONEncoder,
        indent=indent or 2,
        separators=separators,
        default=default or str,
        sort_keys=sort_keys,
        **kw,
    )


__all__ = [
    "JSONDecodeError",
    "JSONDecoder",
    "SmarterJSONEncoder",
    "dumps",
    "load",
    "loads",
]
