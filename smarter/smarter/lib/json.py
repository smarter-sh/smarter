"""
Overridden JSON utilities for the Smarter platform.

This module wraps the standard :mod:`json` library with the following enhancements:

- Uses :class:`SmarterJSONEncoder` as the default encoder.
- Standardizes indentation to 2 characters.
- Falls back to :func:`str` for non-serializable objects.

:class:`SmarterJSONEncoder` adds serialization support for the following types:

- :class:`datetime.datetime`, :class:`datetime.date`, :class:`datetime.time`, :class:`datetime.timedelta`
- :class:`decimal.Decimal`
- :class:`uuid.UUID`
- ``taggit.managers.TaggableManager``

The following symbols are re-exported unmodified from :mod:`json`:

- :exc:`~json.JSONDecodeError`
- :class:`~json.JSONDecoder`
- :func:`~json.load`
- :func:`~json.loads`
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

from pydantic import HttpUrl, TypeAdapter

from smarter.lib import logging

logger = logging.getLogger(__name__)
formatted_logger_prefix = "SmarterJSONEncoder"


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


# pylint: disable=C0209
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
    JSONEncoder subclass that knows how to encode odd types like.

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
        elif isinstance(o, set):
            return list(o)
        elif isinstance(o, HttpUrl):
            return str(o)
        else:
            # Handle Django's GenericRelatedObjectManager and Django's
            # TaggableManager without importing them directly in order to avoid
            # import timing issues during startup.
            if (
                type(o).__name__ == "GenericRelatedObjectManager"
                and getattr(type(o), "__module__", None) == "django.contrib.contenttypes.fields"
            ):
                return list(o.all())

            # Handle TaggedItem
            if type(o).__name__ == "Tag" and getattr(type(o), "__module__", None) == "taggit.models":
                # e.g. a TaggableManager field of model_to_dict(), which is a list of Tags.
                return o.name
            if type(o).__name__ == "TaggedItem" and getattr(type(o), "__module__", None) == "taggit.models":
                retval = o.tag.name
                logger.debug("%s.default() Serializing TaggedItem with tag: %s", formatted_logger_prefix, retval)
                return retval

            # Handle TaggableManager
            if (
                type(o).__name__ in ("TaggableManager", "_TaggableManager")
                and getattr(type(o), "__module__", None) == "taggit.managers"
            ):
                retval = list(o.all().values_list("name", flat=True))
                logger.debug("%s.default() Serializing TaggableManager with tags: %s", formatted_logger_prefix, retval)
                return retval

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
    JSON dump with.

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
        indent=2 if indent is None else indent,
        separators=separators,
        default=default or str,
        sort_keys=sort_keys,
        **kw,
    )


# (context, type) pairs already warned about by SmarterCacheKeyEncoder, so that a hot code
# path logs its fallback once per process rather than on every call.
_cache_key_fallbacks_warned: set[tuple[str, str]] = set()


class SmarterCacheKeyEncoder(SmarterJSONEncoder):
    """
    JSONEncoder subclass for cache keys, used by :func:`dumps_cache_key`.

    A cache key must be the same every time for equal arguments, and different
    for different ones. This encoder therefore:

    - encodes the types that :class:`SmarterJSONEncoder` knows (datetimes,
      Decimals, UUIDs, ...) with that encoder, which :func:`dumps` never does,
      because its ``default=str`` replaces the encoder's own ``default()``;
    - sorts sets, whose iteration order changes from one process to the next;
    - falls back to :func:`str` for any other object, as :func:`dumps` does,
      but logs a warning, once per context and type. ``str()`` of an object
      can collide (two model rows with the same name) or change in every
      process (``<Foo object at 0x...>``), so these fallbacks are being
      found and removed before the fallback itself is.

    :param context: What the key is for, e.g. the qualified name of a cached
        function. It is only used in the warning.
    :type context: str
    """

    def __init__(self, *args, context: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self.context = context

    def default(self, o):
        if isinstance(o, (set, frozenset)):
            return sorted(o, key=lambda item: dumps_cache_key(item, context=self.context))
        try:
            return super().default(o)
        except TypeError:
            type_name = f"{type(o).__module__}.{type(o).__qualname__}"
            if (self.context, type_name) not in _cache_key_fallbacks_warned:
                _cache_key_fallbacks_warned.add((self.context, type_name))
                # the type only, never the value: arguments can hold sensitive data.
                logger.warning(
                    "%s.dumps_cache_key() fell back to str() for a %s in the cache key of %s. "
                    "Cache key arguments should be plain values (str, int, bool, tuples), such as an id.",
                    logging.formatted_text(__name__),
                    type_name,
                    self.context or "an unnamed key",
                )
            return str(o)


def dumps_cache_key(obj, *, context: str = "") -> str:
    """
    Serialize ``obj`` into the canonical JSON text of a cache key.

    The output is compact, with sorted keys and sorted sets, so that equal
    values always produce the same text. See :class:`SmarterCacheKeyEncoder`
    for how other types are encoded, and for the warning it logs when it falls
    back to :func:`str`.

    :param obj: The value to serialize, e.g. a cached function's bound arguments.
    :type obj: object
    :param context: What the key is for, e.g. the qualified name of a cached
        function, named in the fallback warning.
    :type context: str
    :return: The JSON text.
    :rtype: str
    :raises ValueError: If ``obj`` contains a circular reference, or a value
        that :class:`SmarterJSONEncoder` refuses, such as a timezone-aware time.
    """
    return json.dumps(obj, cls=SmarterCacheKeyEncoder, context=context, sort_keys=True, separators=(",", ":"))


__all__ = [
    "JSONDecodeError",
    "JSONDecoder",
    "SmarterCacheKeyEncoder",
    "SmarterJSONEncoder",
    "dumps",
    "dumps_cache_key",
    "load",
    "loads",
]
