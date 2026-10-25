"""
Smarter.lib.cache.keys
======================

This module is also published as the standalone package cache-results
(https://github.com/smarter-sh/cache-results). Make every change in both.

Cache keys for the ``@cache_results`` decorator.

A cache key must be the same every time for equal arguments, in every process,
and different for different ones. This module turns a decorated function and
its arguments into such a key:

- :func:`normalize` converts arguments into JSON-ready values. Dicts and lists
  stay JSON objects and arrays, sets are sorted and tagged, classes and
  dataclasses are tagged with their qualified names.
- :class:`CacheKeyEncoder` serializes the values that JSON doesn't know, such
  as datetimes, Decimals and UUIDs, and **refuses everything else**. ``str()``
  of an arbitrary object is not a safe key: two model rows with the same name
  would share one entry, and ``<Foo object at 0x...>`` changes in every process.
- :func:`make_key` hashes the result into a key that names the function.

This module depends only on Django and the standard library. Projects add
types by subclassing :class:`CacheKeyEncoder` and naming the subclass in the
``KEY_ENCODER`` entry of the ``CACHE_RESULTS`` setting (see
:mod:`smarter.lib.cache.conf`).
"""

import dataclasses
import hashlib
import inspect
import json
from typing import Callable

from django.core.serializers.json import DjangoJSONEncoder


class CacheKeyArgumentError(TypeError):
    """An argument of a cached function can't be part of a cache key."""


class CacheKeyEncoder(DjangoJSONEncoder):
    """
    Strict JSON encoder for cache keys.

    It encodes what :class:`django.core.serializers.json.DjangoJSONEncoder`
    knows (datetimes, dates, times, timedeltas, Decimals, UUIDs and lazy
    translation strings). Any other object raises
    :class:`CacheKeyArgumentError`, so that the call runs uncached rather than
    be cached under an unsafe key. (Sets, classes and dataclasses never reach
    the encoder: :func:`normalize` has already converted them.)

    To support another type, subclass it and override :meth:`default`, then
    name the subclass in ``CACHE_RESULTS["KEY_ENCODER"]``:

    .. code-block:: python

        class MyCacheKeyEncoder(CacheKeyEncoder):
            def default(self, o):
                if isinstance(o, Money):
                    return {"__money__": [str(o.amount), o.currency]}
                return super().default(o)
    """

    def default(self, o):
        """
        Encode one value that JSON doesn't know.

        :param o: The value.
        :type o: object
        :return: A JSON-serializable representation of ``o``.
        :rtype: object
        :raises CacheKeyArgumentError: If ``o`` has no safe representation.
        """
        try:
            return super().default(o)
        except TypeError as e:
            raise CacheKeyArgumentError(
                f"a {type(o).__module__}.{type(o).__qualname__} can't be part of a cache key. "
                "Pass plain values (str, int, bool, tuples), such as an id."
            ) from e


def dumps(obj: object, encoder: type[CacheKeyEncoder] = CacheKeyEncoder) -> str:
    """
    Serialize a normalized value into compact, canonical JSON text.

    :param obj: A value returned by :func:`normalize`.
    :type obj: object
    :param encoder: The JSON encoder.
    :type encoder: type[CacheKeyEncoder]
    :return: The JSON text, with sorted keys.
    :rtype: str
    :raises CacheKeyArgumentError: If a value can't be part of a key.
    """
    return json.dumps(obj, cls=encoder, sort_keys=True, separators=(",", ":"))


def normalize(obj: object, encoder: type[CacheKeyEncoder] = CacheKeyEncoder) -> object:
    """
    Convert an argument into a JSON-ready value that is the same for equal arguments.

    Dicts and lists are kept as JSON objects and arrays, so that ``{"a": 1}``
    and ``[("a", 1)]`` don't share a key. Sets are sorted by the JSON text of
    their members, because their iteration order changes from one process to
    the next, and tagged, so that they don't share a key with a list. A class, e.g. the
    ``cls`` of a classmethod, is identified by its module and qualified name.
    A dataclass instance is identified by its class and its fields, so that
    frozen value objects can be arguments.

    :param obj: An argument of the decorated function.
    :type obj: object
    :param encoder: The JSON encoder, used to sort set members.
    :type encoder: type[CacheKeyEncoder]
    :return: The normalized value.
    :rtype: object
    :raises CacheKeyArgumentError: If a set member can't be part of a key.
    """
    if isinstance(obj, dict):
        return {key: normalize(value, encoder) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [normalize(item, encoder) for item in obj]
    if isinstance(obj, (set, frozenset)):
        items = [normalize(item, encoder) for item in obj]
        return {"__set__": sorted(items, key=lambda item: dumps(item, encoder))}
    if isinstance(obj, type):
        return {"__class__": f"{obj.__module__}.{obj.__qualname__}"}
    if dataclasses.is_dataclass(obj):
        fields = {field.name: normalize(getattr(obj, field.name), encoder) for field in dataclasses.fields(obj)}
        return {"__dataclass__": f"{type(obj).__module__}.{type(obj).__qualname__}", "fields": fields}
    return obj


def bind_arguments(func: Callable, args: tuple, kwargs: dict) -> tuple[tuple, dict]:
    """
    Bind arguments to the function's signature, with its defaults applied.

    ``f(1, b=2)``, ``f(a=1, b=2)`` and ``f(1)`` (when ``b`` defaults to 2)
    then produce the same key. Otherwise a function and its ``invalidate()``
    could silently compute different keys depending on how each was called.

    :param func: The decorated function.
    :type func: Callable
    :param args: The positional arguments.
    :type args: tuple
    :param kwargs: The keyword arguments.
    :type kwargs: dict
    :return: Empty positional arguments and every argument by name, or the
        arguments unchanged if they don't fit the signature.
    :rtype: tuple[tuple, dict]
    """
    try:
        bound = inspect.signature(func).bind(*args, **kwargs)
    except (TypeError, ValueError):
        return args, kwargs
    bound.apply_defaults()
    return (), dict(bound.arguments)


def make_key(
    func: Callable,
    args: tuple,
    kwargs: dict,
    encoder: type[CacheKeyEncoder] = CacheKeyEncoder,
    prefix: str = "",
) -> str:
    """
    Return the cache key of one call of a decorated function.

    The key is the prefix, the function's module and qualified name, and a
    32-character SHA-256 hash of its bound, normalized and serialized
    arguments, e.g. ``myapp.views.lookup()_3f0c...``.

    :param func: The decorated function.
    :type func: Callable
    :param args: The positional arguments.
    :type args: tuple
    :param kwargs: The keyword arguments.
    :type kwargs: dict
    :param encoder: The JSON encoder for the arguments.
    :type encoder: type[CacheKeyEncoder]
    :param prefix: Text that starts every key, e.g. to version them.
    :type prefix: str
    :return: The cache key.
    :rtype: str
    :raises CacheKeyArgumentError: If an argument can't be part of a key.
    :raises ValueError: If an argument contains a circular reference, or a
        value that the encoder refuses, such as a timezone-aware time.
    :raises RecursionError: If an argument is nested too deeply.
    """
    args, kwargs = bind_arguments(func, args, kwargs)
    key_data = [func.__qualname__, normalize(args, encoder), normalize(kwargs, encoder)]
    text = dumps(key_data, encoder)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
    return f"{prefix}{func.__module__}.{func.__qualname__}()_{digest}"


def describe_key_error(error: Exception) -> str:
    """
    Return a short description of why a key couldn't be made, without argument values.

    :param error: The exception that :func:`make_key` raised.
    :type error: Exception
    :return: The description.
    :rtype: str
    """
    if isinstance(error, CacheKeyArgumentError):
        return str(error)
    if isinstance(error, RecursionError):
        return "an argument is nested too deeply, or refers to itself."
    return f"{type(error).__name__}: {error}"


__all__ = [
    "CacheKeyArgumentError",
    "CacheKeyEncoder",
    "bind_arguments",
    "describe_key_error",
    "dumps",
    "make_key",
    "normalize",
]
