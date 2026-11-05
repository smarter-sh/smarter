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
import functools
import json
import logging as std_logging
import uuid
from collections.abc import Callable

# pylint: disable=unused-import
from json import (  # unmodified re-export
    JSONDecodeError,
    JSONDecoder,
    load,
    loads,
)
from typing import Any, Optional

from django.utils.functional import Promise
from pydantic import HttpUrl, TypeAdapter

# The standard library's logging, not smarter.lib.logging: smarter.lib.logging imports
# this module (through console_helpers), so importing it here would be circular.
# smarter.lib.logging.getLogger is this same function.
logger = std_logging.getLogger(__name__)


def _logger_prefix() -> str:
    """
    Return this module's formatted log prefix.

    ``console_helpers`` is imported on use, not at import, because it imports this module.

    :returns: The formatted module name.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.common.helpers.console_helpers import SmarterFormattedText

    return SmarterFormattedText.text(__name__)


def _get_duration_components(duration: datetime.timedelta) -> tuple[int, int, int, int, int]:
    """
    Split a timedelta into days, hours, minutes, seconds and microseconds.

    :param duration: The timedelta.
    :returns: A tuple of ``(days, hours, minutes, seconds, microseconds)``.
    """
    days = duration.days
    seconds = duration.seconds
    microseconds = duration.microseconds

    minutes = seconds // 60
    seconds %= 60

    hours = minutes // 60
    minutes %= 60

    components = (days, hours, minutes, seconds, microseconds)
    return components


def is_aware(value: datetime.datetime | datetime.time) -> bool:
    """
    Return whether a datetime or time is timezone-aware.

    The concept is defined in Python's docs:
    https://docs.python.org/library/datetime.html#datetime.tzinfo

    :param value: The datetime or time.
    :returns: True if ``value.utcoffset()`` is not None.
    """
    offset = value.utcoffset()
    return offset is not None


def duration_iso_string(duration: datetime.timedelta) -> str:
    """
    Format a timedelta as an ISO 8601 duration, e.g. ``P1DT02H03M04.000005S``.

    :param duration: The timedelta; a negative one is prefixed with ``-``.
    :returns: The ISO 8601 string.
    """
    if duration < datetime.timedelta(0):
        sign = "-"
        duration *= -1
    else:
        sign = ""

    days, hours, minutes, seconds, microseconds = _get_duration_components(duration)
    ms = ""
    if microseconds:
        ms = f".{microseconds:06d}"
    iso_string = f"{sign}P{days}DT{hours:02d}H{minutes:02d}M{seconds:02d}{ms}S"
    return iso_string


def _is_class(o: object, module: str, *names: str) -> bool:
    """
    Return whether ``o``'s class has one of ``names`` and is defined in ``module``.

    It identifies a class by name, so that the class need not be imported, e.g. to avoid
    import timing issues during startup.

    :param o: The value.
    :param module: The dotted name of the module that defines the class.
    :param names: The class names to accept.
    :returns: True if ``type(o).__name__`` is one of ``names`` and ``type(o).__module__`` is
        ``module``.
    """
    value_class = type(o)
    if value_class.__name__ not in names:
        return False
    class_module = getattr(value_class, "__module__", None)
    return class_module == module


class SmarterJSONEncoder(json.JSONEncoder):
    """
    A JSON encoder for the types that :class:`json.JSONEncoder` can't serialize.

    It handles dates and times, decimals, UUIDs, Django's lazy strings, sets, Pydantic urls,
    generic relations and taggit's tags and managers. :func:`dumps` uses it by default, and
    Django model fields use it as their ``encoder``.
    """

    def default(self, o: Any) -> Any:
        """
        Encode a value that :class:`json.JSONEncoder` can't.

        Datetimes, dates and times become ISO 8601 strings, timedeltas ISO 8601 durations,
        decimals, UUIDs, lazy strings and urls strings, sets lists, and generic relations and
        taggit tags their names or lists.

        :param o: The value.
        :returns: A JSON-serializable value.
        :raises ValueError: For a timezone-aware time.
        :raises TypeError: For any other type, from :meth:`json.JSONEncoder.default`.
        """
        # Types that json.JSONEncoder handles itself never reach default(). When called
        # directly, pass them to super().default(), which raises TypeError.
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
            if _is_class(o, "django.contrib.contenttypes.fields", "GenericRelatedObjectManager"):
                return list(o.all())

            # Handle TaggedItem
            if _is_class(o, "taggit.models", "Tag"):
                # e.g. a TaggableManager field of model_to_dict(), which is a list of Tags.
                return o.name
            if _is_class(o, "taggit.models", "TaggedItem"):
                retval = o.tag.name
                logger.debug(
                    "%s.SmarterJSONEncoder.default() Serializing TaggedItem with tag: %s", _logger_prefix(), retval
                )
                return retval

            # Handle TaggableManager
            if _is_class(o, "taggit.managers", "TaggableManager", "_TaggableManager"):
                retval = list(o.all().values_list("name", flat=True))
                logger.debug(
                    "%s.SmarterJSONEncoder.default() Serializing TaggableManager with tags: %s",
                    _logger_prefix(),
                    retval,
                )
                return retval

            return super().default(o)


@functools.cache
def with_str_fallback(encoder_class: type[json.JSONEncoder]) -> type[json.JSONEncoder]:
    """
    Return a subclass of ``encoder_class`` that serializes any value it can't encode with :func:`str`.

    The encoder's own :meth:`~json.JSONEncoder.default` runs first, so its types keep their
    format, e.g. a datetime is still an ISO 8601 string. The subclass is built once per
    encoder class.

    :param encoder_class: The encoder to extend.
    :returns: The extended encoder class.
    """

    class StrFallbackEncoder(encoder_class):
        """Encode with ``encoder_class``, else with :func:`str`."""

        def default(self, o: Any) -> Any:
            """
            Encode ``o`` with the parent encoder, else as ``str(o)``.

            :param o: The value.
            :returns: A JSON-serializable value.
            """
            try:
                return super().default(o)
            except TypeError:
                return str(o)

    StrFallbackEncoder.__name__ = f"{encoder_class.__name__}WithStrFallback"
    return StrFallbackEncoder


def dumps(
    obj: object,
    *,
    skipkeys: bool = False,
    ensure_ascii: bool = True,
    check_circular: bool = True,
    allow_nan: bool = True,
    cls: type[json.JSONEncoder] | None = None,
    indent: int | str | None = None,
    separators: tuple[str, str] | None = None,
    default: Callable[[object], object] | None = None,
    sort_keys: bool = False,
    **kw: object,
) -> str:
    """
    Serialize ``obj`` to a JSON string, with Smarter's defaults.

    The arguments are those of :func:`json.dumps`, with these defaults:

    - ``cls`` is :class:`SmarterJSONEncoder`.
    - ``indent`` is 2.
    - A value that the encoder can't serialize becomes ``str(value)``, unless ``default``
      is given. The encoder still handles its own types first.

    :param obj: The value to serialize.
    :returns: The JSON string.
    """
    encoder_class = cls
    if encoder_class is None:
        encoder_class = SmarterJSONEncoder
    if default is None:
        encoder_class = with_str_fallback(encoder_class)

    if indent is None:
        indent = 2

    return json.dumps(
        obj,
        skipkeys=skipkeys,
        ensure_ascii=ensure_ascii,
        check_circular=check_circular,
        allow_nan=allow_nan,
        cls=encoder_class,
        indent=indent,
        separators=separators,
        default=default,
        sort_keys=sort_keys,
        **kw,
    )


def to_jsonable(obj: Any, cls: Optional[type[json.JSONEncoder]] = None) -> Any:
    """
    Return ``obj`` as plain JSON data: dicts, lists, strings, numbers, booleans and None.

    It is ``json.loads(dumps(obj))``, without the indentation: an indented dump runs in pure
    Python, while a compact one runs in the standard library's C encoder. Use it to snapshot
    data, e.g. before storing it in a ``JSONField``.

    :param obj: The value to convert.
    :param cls: The encoder; :class:`SmarterJSONEncoder` by default. Values it can't encode
        become ``str(value)``.
    :returns: The JSON data.
    """
    encoder_class = cls
    if encoder_class is None:
        encoder_class = SmarterJSONEncoder
    encoder_class = with_str_fallback(encoder_class)
    text = json.dumps(obj, cls=encoder_class, separators=(",", ":"))
    data = json.loads(text)
    return data


__all__ = [
    "JSONDecodeError",
    "JSONDecoder",
    "SmarterJSONEncoder",
    "dumps",
    "load",
    "loads",
    "to_jsonable",
]
