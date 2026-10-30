"""
Annotation selectors: filter resources by their annotations.

The syntax is that of Kubernetes label selectors, one requirement at a time. Several
requirements must all match. Values are free text and may contain commas, so a selector is a
list of requirements, not one comma-separated string. See
:class:`smarter.lib.annotation.contract.AnnotationRequirement`.

**Example:**

.. code-block:: python

    from smarter.apps.llmclient.models import LLMClient
    from smarter.lib.annotation.selectors import filter_by_annotations

    filter_by_annotations(LLMClient.objects.all(), ["acme.com/crm-account-id=A-10042", "!acme.com/archived"])
"""

from collections.abc import Iterable
from typing import Optional, TypeVar, Union

from django.db import models
from django.db.models.query import QuerySet

from .contract import AnnotationRequirement
from .models import Annotation, annotation_content_type
from .validation import SmarterAnnotationError, validate_annotation_key

QuerySetType = TypeVar("QuerySetType", bound=QuerySet)

AnnotationSelector = Union[None, str, Iterable[Union[str, AnnotationRequirement]]]
"""One requirement, a list of them, or ``None`` for no requirement."""


def parse_annotation_requirement(requirement: str) -> AnnotationRequirement:
    """
    Parse one requirement, e.g. ``acme.com/crm-id=A-10042``.

    :param requirement: ``key``, ``!key``, ``key=value``, ``key==value`` or ``key!=value``.
    :type requirement: str
    :raises SmarterAnnotationError: If the requirement or its key is invalid.
    :returns: The requirement.
    :rtype: AnnotationRequirement
    """
    text = requirement.strip()
    if not text:
        raise SmarterAnnotationError("An annotation selector requirement can't be empty.")
    if text.startswith("!"):
        return AnnotationRequirement(key=validate_annotation_key(text[1:].strip()), operator="not_exists")
    equals = text.find("=")
    if equals < 0:
        return AnnotationRequirement(key=validate_annotation_key(text), operator="exists")
    value = text[equals + 1 :]
    if equals > 0 and text[equals - 1] == "!":
        return AnnotationRequirement(
            key=validate_annotation_key(text[: equals - 1].strip()), operator="not_equals", value=value
        )
    if value.startswith("="):
        value = value[1:]
    return AnnotationRequirement(key=validate_annotation_key(text[:equals].strip()), operator="equals", value=value)


def parse_annotation_selector(selector: AnnotationSelector) -> list[AnnotationRequirement]:
    """
    Parse a selector into its requirements.

    :param selector: One requirement, a list of them, or ``None``.
    :type selector: AnnotationSelector
    :raises SmarterAnnotationError: If a requirement is invalid.
    :returns: The requirements, empty for ``None``.
    :rtype: list[AnnotationRequirement]
    """
    if selector is None:
        return []
    if isinstance(selector, str):
        selector = [selector]
    return [
        item if isinstance(item, AnnotationRequirement) else parse_annotation_requirement(item)
        for item in selector
        if isinstance(item, AnnotationRequirement) or (isinstance(item, str) and item.strip())
    ]


def filter_by_annotations(queryset: QuerySetType, selector: AnnotationSelector) -> QuerySetType:
    """
    Return the resources of ``queryset`` that match every requirement of ``selector``.

    As in Kubernetes, ``key!=value`` also matches resources that don't have the key.

    :param queryset: Resources of one model, e.g. ``LLMClient.objects.with_read_permission_for(user)``.
    :type queryset: QuerySet
    :param selector: One requirement, a list of them, or ``None``.
    :type selector: AnnotationSelector
    :raises SmarterAnnotationError: If a requirement is invalid.
    :returns: The filtered queryset.
    :rtype: QuerySet
    """
    requirements = parse_annotation_selector(selector)
    if not requirements:
        return queryset
    content_type = annotation_content_type(queryset.model)
    for requirement in requirements:
        value: Optional[str] = requirement.value if requirement.operator in ("equals", "not_equals") else None
        matching = Annotation.objects.filter(content_type=content_type).with_key(requirement.key, value)
        object_ids = matching.object_ids_for(queryset.model)
        if requirement.operator in ("exists", "equals"):
            queryset = queryset.filter(pk__in=object_ids)
        else:
            queryset = queryset.exclude(pk__in=object_ids)
    return queryset


def model_with_annotation(model: type[models.Model], key: str, value: Optional[str] = None) -> QuerySet:
    """
    Return every resource of ``model`` that has the annotation ``key``, with ``value`` if given.

    :param model: The model, e.g. ``LLMClient``.
    :type model: type[models.Model]
    :param key: The annotation key.
    :type key: str
    :param value: The value to match, or ``None`` for any value.
    :type value: Optional[str]
    :returns: The resources.
    :rtype: QuerySet
    """
    requirement = AnnotationRequirement(
        key=validate_annotation_key(key), operator="exists" if value is None else "equals", value=value
    )
    return filter_by_annotations(model._default_manager.all(), [requirement])  # pylint: disable=W0212


__all__ = [
    "AnnotationSelector",
    "QuerySetType",
    "filter_by_annotations",
    "model_with_annotation",
    "parse_annotation_requirement",
    "parse_annotation_selector",
]
