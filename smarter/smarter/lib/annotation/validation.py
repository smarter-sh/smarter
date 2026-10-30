"""
Validation and normalization of Smarter annotations.

Smarter annotations follow Kubernetes annotations: a map of string keys to string values that
any client or extension may attach to a resource, for its own purposes. A key is an optional
DNS-subdomain prefix that names its owner, e.g. ``acme.com``, then a slash and a name, e.g.
``acme.com/crm-account-id``. Smarter's keys are a superset of Kubernetes keys: the name may have
several slash-separated segments, e.g. ``smarter.sh/llmclient/use-case``. Every valid Kubernetes
key is a valid Smarter key.

The functions here are the one place that decides what a valid annotation is. The SAM manifest
models, the ``MetaDataModel.annotations`` setter, and the data migrations all call them.
"""

import datetime
import decimal
import json
import re
import uuid
from typing import Optional, Union

from smarter.common.exceptions import SmarterValueError
from smarter.lib.typing import SmarterDictType

from .const import (
    ANNOTATION_KEY_MAX_LENGTH,
    ANNOTATION_KEY_PREFIX_MAX_LENGTH,
    ANNOTATION_KEY_SEGMENT_MAX_LENGTH,
    ANNOTATIONS_TOTAL_MAX_BYTES,
    RESERVED_ANNOTATION_PREFIXES,
)

DNS_LABEL = r"[a-z0-9]([-a-z0-9]*[a-z0-9])?"
DNS_SUBDOMAIN_PATTERN = re.compile(rf"^{DNS_LABEL}(\.{DNS_LABEL})*$")
"""A DNS subdomain as Kubernetes defines it (RFC 1123): lowercase labels separated by dots."""

NAME_SEGMENT_PATTERN = re.compile(r"^([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9]$")
"""A Kubernetes qualified name: alphanumeric at both ends, with ``-``, ``_`` and ``.`` between."""

AnnotationsMap = dict[str, str]
"""A resource's annotations: string keys mapped to string values, as in Kubernetes."""

AnnotationsInput = Union[None, str, SmarterDictType, list[SmarterDictType]]
"""
What callers may pass as annotations.

A map, the legacy list of one-key maps, either of
them as a JSON string, or ``None``.
"""


class SmarterAnnotationError(SmarterValueError):
    """Raised for an invalid annotation key, value or set of annotations."""


def split_annotation_key(key: str) -> tuple[Optional[str], str]:
    """
    Split an annotation key into its prefix and its name.

    The prefix is everything before the first slash. A key without a slash has no prefix.

    **Example:**

    .. code-block:: python

        split_annotation_key("acme.com/crm/account-id")  # ("acme.com", "crm/account-id")
        split_annotation_key("owner")                    # (None, "owner")

    :param key: The annotation key.
    :type key: str
    :returns: The prefix, or ``None``, and the name.
    :rtype: tuple[Optional[str], str]
    """
    if "/" in key:
        prefix, name = key.split("/", 1)
        return prefix, name
    return None, key


def validate_annotation_key(key: str) -> str:
    """
    Validate an annotation key, and return it.

    A key is ``[prefix/]name``. The prefix, when present, is a DNS subdomain of at most 253
    characters. The name is one or more segments separated by slashes. Each segment is at most 63
    characters, alphanumeric at both ends, with ``-``, ``_`` and ``.`` between. The whole key is
    at most 317 characters.

    :param key: The annotation key.
    :type key: str
    :raises SmarterAnnotationError: If the key is not valid.
    :returns: The key.
    :rtype: str
    """
    if not isinstance(key, str) or not key:
        raise SmarterAnnotationError(f"Annotation keys must be non-empty strings, got {key!r}.")
    if len(key) > ANNOTATION_KEY_MAX_LENGTH:
        raise SmarterAnnotationError(
            f"Annotation key {key!r} is {len(key)} characters long. The limit is {ANNOTATION_KEY_MAX_LENGTH}."
        )
    prefix, name = split_annotation_key(key)
    if prefix is not None:
        if len(prefix) > ANNOTATION_KEY_PREFIX_MAX_LENGTH or not DNS_SUBDOMAIN_PATTERN.match(prefix):
            raise SmarterAnnotationError(
                f"Annotation key {key!r} has an invalid prefix {prefix!r}. A prefix must be a lowercase DNS "
                f"subdomain of at most {ANNOTATION_KEY_PREFIX_MAX_LENGTH} characters, e.g. 'acme.com'."
            )
    for segment in name.split("/"):
        if len(segment) > ANNOTATION_KEY_SEGMENT_MAX_LENGTH or not NAME_SEGMENT_PATTERN.match(segment):
            raise SmarterAnnotationError(
                f"Annotation key {key!r} has an invalid name segment {segment!r}. Each part of the name between "
                f"slashes must be 1 to {ANNOTATION_KEY_SEGMENT_MAX_LENGTH} characters, begin and end with a letter "
                "or digit, and contain only letters, digits, '-', '_' and '.'."
            )
    return key


def coerce_annotation_value(key: str, value: object, lenient: bool = False) -> str:
    """
    Return an annotation's value as a string.

    Annotation values are strings, as in Kubernetes. YAML parses unquoted scalars such as ``true``,
    ``42`` or ``2026-10-28`` as other types, so they are converted to the string that was written:
    booleans to ``"true"`` or ``"false"``, dates to ISO 8601, ``None`` to ``""``.

    :param key: The annotation's key, for the error message.
    :type key: str
    :param value: The value.
    :type value: object
    :param lenient: Encode lists and dicts as JSON instead of rejecting them. Only data migrations
        of legacy rows set this.
    :type lenient: bool
    :raises SmarterAnnotationError: If the value is a list, a dict, or bytes that aren't UTF-8.
    :returns: The value as a string.
    :rtype: str
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float, decimal.Decimal, uuid.UUID)):
        return str(value)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError as e:
            raise SmarterAnnotationError(f"Annotation {key!r} has a bytes value that is not UTF-8.") from e
    if isinstance(value, (list, dict)) and lenient:
        return json.dumps(value, default=str)
    raise SmarterAnnotationError(
        f"Annotation {key!r} has a {type(value).__name__} value. Annotation values are strings: "
        "to store structured data, quote it as a JSON string."
    )


def annotations_size(annotations: AnnotationsMap) -> int:
    """
    Return the size of a resource's annotations in bytes: every key and value, UTF-8 encoded.

    :param annotations: The annotations.
    :type annotations: AnnotationsMap
    :returns: The size in bytes.
    :rtype: int
    """
    return sum(len(key.encode("utf-8")) + len(value.encode("utf-8")) for key, value in annotations.items())


def normalize_annotations(value: AnnotationsInput, lenient: bool = False) -> AnnotationsMap:
    """
    Return annotations in any accepted shape as a validated map of strings to strings.

    Accepts the Kubernetes map, ``{"acme.com/crm-id": "42"}``, and the list of one-key maps that
    older SAM manifests use, ``[{"acme.com/crm-id": "42"}]``, or either one as a JSON string.

    **Example:**

    .. code-block:: python

        normalize_annotations([{"acme.com/active": True}])  # {"acme.com/active": "true"}

    :param value: The annotations.
    :type value: AnnotationsInput
    :param lenient: For legacy rows in data migrations: skip invalid keys, keep the last value of a
        duplicate key, encode lists and dicts as JSON, and don't enforce the size limit.
    :type lenient: bool
    :raises SmarterAnnotationError: If a key or value is invalid, a key appears twice, or the
        annotations are larger than 256 KiB.
    :returns: The annotations, in their original order.
    :rtype: AnnotationsMap
    """
    if value is None or value == "":
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as e:
            raise SmarterAnnotationError(f"Annotations could not be parsed as JSON: {e}") from e
    if isinstance(value, dict):
        pairs = list(value.items())
    elif isinstance(value, list):
        pairs = []
        for item in value:
            if not isinstance(item, dict):
                if lenient:
                    continue
                raise SmarterAnnotationError(
                    f"Each item of a list of annotations must be a key-value map, got {type(item).__name__}: {item!r}"
                )
            pairs.extend(item.items())
    else:
        raise SmarterAnnotationError(f"Annotations must be a map of keys to values, got {type(value).__name__}.")

    retval: AnnotationsMap = {}
    for key, item_value in pairs:
        try:
            validate_annotation_key(key)
            if key in retval and not lenient:
                raise SmarterAnnotationError(f"Annotation key {key!r} appears more than once.")
            retval[key] = coerce_annotation_value(key, item_value, lenient=lenient)
        except SmarterAnnotationError:
            if not lenient:
                raise
    if not lenient and annotations_size(retval) > ANNOTATIONS_TOTAL_MAX_BYTES:
        raise SmarterAnnotationError(
            f"Annotations are {annotations_size(retval)} bytes. The limit is {ANNOTATIONS_TOTAL_MAX_BYTES} bytes."
        )
    return retval


def prefix_matches(prefix: Optional[str], owner: str) -> bool:
    """
    Return whether a key's prefix is ``owner`` or one of its subdomains.

    **Example:**

    .. code-block:: python

        prefix_matches("crm.acme.com", "acme.com")  # True
        prefix_matches("notacme.com", "acme.com")   # False

    :param prefix: A key's prefix, from :func:`split_annotation_key`.
    :type prefix: Optional[str]
    :param owner: A DNS domain, e.g. ``acme.com``.
    :type owner: str
    :returns: True if the prefix belongs to the owner.
    :rtype: bool
    """
    if not prefix:
        return False
    return prefix == owner or prefix.endswith("." + owner)


def is_reserved_annotation_key(key: str) -> bool:
    """
    Return whether a key belongs to the Smarter platform: its prefix is ``smarter.sh`` or a subdomain.

    :param key: The annotation key.
    :type key: str
    :returns: True if the key's prefix is reserved.
    :rtype: bool
    """
    prefix, _ = split_annotation_key(key)
    return any(prefix_matches(prefix, reserved) for reserved in RESERVED_ANNOTATION_PREFIXES)


__all__ = [
    "AnnotationsInput",
    "AnnotationsMap",
    "SmarterAnnotationError",
    "annotations_size",
    "coerce_annotation_value",
    "is_reserved_annotation_key",
    "normalize_annotations",
    "prefix_matches",
    "split_annotation_key",
    "validate_annotation_key",
]
