"""
The Annotation model: one row per annotation of a Smarter resource.

Annotations belong to :class:`smarter.lib.django.models.MetaDataModel`, which is abstract, so a
row points at its resource through Django's content types framework, as django-taggit's tags do:
a ``content_type`` and an ``object_id``. A resource that uses multi-table inheritance, e.g. a
``PluginMetaStatic``, keeps its annotations under its root model, ``PluginMeta``, the table that
holds its metadata, so that both classes see the same annotations.
"""

from collections.abc import Iterable
from typing import Optional, Union

from cache_results import cache_results
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.db.models.functions import Cast
from django.db.models.query import QuerySet

from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.models.timestamped_model import TimestampedModel

from .const import ANNOTATION_KEY_MAX_LENGTH, ANNOTATION_KEY_PREFIX_MAX_LENGTH
from .contract import AnnotationChange
from .validation import AnnotationsMap, split_annotation_key

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)

ModelOrInstance = Union[type[models.Model], models.Model]
"""A Django model class, or one of its instances."""


def annotation_root_model(model: ModelOrInstance) -> type[models.Model]:
    """
    Return the model under which a resource's annotations are stored.

    That is the resource's farthest concrete ancestor: the model itself, unless it uses
    multi-table inheritance. Proxy models resolve to their concrete model.

    :param model: A model class or instance.
    :type model: ModelOrInstance
    :returns: The root model.
    :rtype: type[models.Model]
    """
    # pylint: disable=W0212
    concrete = model._meta.concrete_model
    if concrete is None:
        raise TypeError(f"{model} is not a concrete Django model.")
    parents = concrete._meta.get_parent_list()
    return parents[-1] if parents else concrete


def annotation_content_type(model: ModelOrInstance) -> ContentType:
    """
    Return the content type under which a resource's annotations are stored.

    :param model: A model class or instance.
    :type model: ModelOrInstance
    :returns: The content type of :func:`annotation_root_model`.
    :rtype: ContentType
    """
    return ContentType.objects.get_for_model(annotation_root_model(model))


@cache_results(timeout=smarter_settings.cache_expiration)
def get_cached_annotations(content_type_id: int, pk: str) -> AnnotationsMap:
    """
    Return the annotations of one resource, from the cache when possible.

    Invalidated, once the transaction commits, whenever one of the resource's rows is saved or
    deleted, however that happens: by :meth:`AnnotationQuerySet.sync`, by the Django admin, or
    directly (see :mod:`smarter.lib.annotation.receivers`).

    :param content_type_id: The id of the resource's content type, from :func:`annotation_content_type`.
    :type content_type_id: int
    :param pk: The resource's primary key, as a string.
    :type pk: str
    :returns: The annotations, in the order they were added.
    :rtype: AnnotationsMap
    """
    rows = Annotation.objects.filter(content_type_id=content_type_id, object_id=pk).order_by("id")
    return {row.key: row.value for row in rows}


def prefetch_annotations(instances: Iterable[models.Model]) -> None:
    """
    Read the annotations of many resources at once, in one query per kind.

    This is ``prefetch_related()`` for annotations, which aren't a relation that Django can
    prefetch. A list that shows every resource's annotations calls it with a page of resources,
    so that the page doesn't cost one query per resource. Each instance then answers
    :attr:`smarter.lib.django.models.MetaDataModel.annotations` from what was read, until its
    annotations are next assigned or saved. Instances that have no annotations are skipped.

    **Example:**

    .. code-block:: python

        page = list(LLMClient.objects.filter(user_profile=user_profile)[:50])
        prefetch_annotations(page)
        [llmclient.annotations for llmclient in page]  # no more queries

    :param instances: The resources, of one kind or several.
    :type instances: Iterable[models.Model]
    """
    # pylint: disable=import-outside-toplevel
    from smarter.lib.django.models import MetaDataModel

    by_content_type: dict[int, dict[str, list[MetaDataModel]]] = {}
    for instance in instances:
        if not isinstance(instance, MetaDataModel) or instance.pk is None:
            continue
        content_type_id = annotation_content_type(instance).pk
        by_content_type.setdefault(content_type_id, {}).setdefault(str(instance.pk), []).append(instance)
    for content_type_id, by_pk in by_content_type.items():
        found: dict[str, AnnotationsMap] = {pk: {} for pk in by_pk}
        rows = Annotation.objects.filter(content_type_id=content_type_id, object_id__in=list(by_pk)).order_by("id")
        for object_id, key, value in rows.values_list("object_id", "key", "value"):
            found[object_id][key] = value
        for pk, annotations in found.items():
            for instance in by_pk[pk]:
                instance._prefetched_annotations = dict(annotations)  # pylint: disable=protected-access


class AnnotationQuerySet(QuerySet["Annotation"]):
    """Queries of annotations, across one resource, one kind, or every kind."""

    def for_model(self, model: ModelOrInstance) -> "AnnotationQuerySet":
        """
        Return the annotations of every resource of a model, e.g. every LLMClient.

        :param model: A model class or instance.
        :type model: ModelOrInstance
        :returns: The annotations.
        :rtype: AnnotationQuerySet
        """
        return self.filter(content_type=annotation_content_type(model))

    def for_object(self, instance: models.Model) -> "AnnotationQuerySet":
        """
        Return the annotations of one resource.

        :param instance: The resource.
        :type instance: models.Model
        :returns: The annotations.
        :rtype: AnnotationQuerySet
        """
        return self.filter(content_type=annotation_content_type(instance), object_id=str(instance.pk))

    def with_key(self, key: str, value: Optional[str] = None) -> "AnnotationQuerySet":
        """
        Return the annotations with a key, and optionally a value.

        :param key: The annotation key, e.g. ``acme.com/crm-account-id``.
        :type key: str
        :param value: The value to match exactly, or ``None`` for any value.
        :type value: Optional[str]
        :returns: The annotations.
        :rtype: AnnotationQuerySet
        """
        queryset = self.filter(key=key)
        if value is not None:
            queryset = queryset.filter(value=value)
        return queryset

    def with_prefix(self, prefix: str) -> "AnnotationQuerySet":
        """
        Return the annotations whose key's prefix is ``prefix``, or one of its subdomains.

        :param prefix: A DNS domain, e.g. ``acme.com``.
        :type prefix: str
        :returns: The annotations.
        :rtype: AnnotationQuerySet
        """
        return self.filter(models.Q(prefix=prefix) | models.Q(prefix__endswith="." + prefix))

    def object_ids_for(self, model: ModelOrInstance) -> QuerySet:
        """
        Return the ``object_id`` of each annotation, as the primary key type of ``model``, for a subquery.

        ``object_id`` is a string, because some resources' primary keys are. Casting it back to an
        integer key lets the database compare it with the resource table's index.

        **Example:**

        .. code-block:: python

            LLMClient.objects.filter(pk__in=Annotation.objects.with_key("acme.com/id").object_ids_for(LLMClient))

        :param model: The resources' model.
        :type model: ModelOrInstance
        :returns: A single-column queryset of primary keys.
        :rtype: QuerySet
        """
        # pylint: disable=W0212
        pk_field = annotation_root_model(model)._meta.pk  # pylint: disable=W0212
        if isinstance(pk_field, (models.AutoField, models.BigAutoField, models.IntegerField)):
            return self.annotate(resource_pk=Cast("object_id", models.BigIntegerField())).values("resource_pk")
        return self.values("object_id")

    def resources(self) -> list[models.Model]:
        """
        Return the resources, of any kind, that these annotations belong to.

        This is the lookup from a key in another system to the Smarter resources that are associated
        with it, e.g. every resource annotated ``acme.com/crm-account-id=A-10042``. Resources are
        returned as their root model (see :func:`annotation_root_model`), and are not filtered by
        any user's permissions.

        **Example:**

        .. code-block:: python

            Annotation.objects.with_key("acme.com/crm-account-id", "A-10042").resources()

        :returns: The resources, ordered by kind, then primary key.
        :rtype: list[models.Model]
        """
        ids_by_content_type: dict[int, set[str]] = {}
        for content_type_id, object_id in self.values_list("content_type_id", "object_id"):
            ids_by_content_type.setdefault(content_type_id, set()).add(object_id)
        retval: list[models.Model] = []
        for content_type_id in sorted(ids_by_content_type):
            model = ContentType.objects.get_for_id(content_type_id).model_class()
            if model is None:
                continue
            # pylint: disable=W0212
            # pylint: disable=W0212
            retval.extend(model._default_manager.filter(pk__in=ids_by_content_type[content_type_id]).order_by("pk"))
        return retval

    def sync(self, instance: models.Model, annotations: AnnotationsMap) -> list[AnnotationChange]:
        """
        Make a resource's annotations exactly ``annotations``, and return what changed.

        Keys that aren't in ``annotations`` are removed, as ``kubectl apply`` does with a manifest's
        annotations. Registered annotation handlers, and the ``annotations_changed`` signal, are sent
        the changes once the transaction commits.

        :param instance: The resource, already saved.
        :type instance: models.Model
        :param annotations: The resource's annotations, already validated.
        :type annotations: AnnotationsMap
        :returns: The changes, in key order.
        :rtype: list[AnnotationChange]
        """
        # pylint: disable=import-outside-toplevel
        from .handlers import dispatch_annotation_changes

        content_type = annotation_content_type(instance)
        # annotations read by prefetch_annotations() are about to be out of date.
        if hasattr(instance, "_prefetched_annotations"):
            instance._prefetched_annotations = None  # pylint: disable=protected-access
        with transaction.atomic():
            existing = {
                row.key: row
                for row in self.select_for_update().filter(content_type=content_type, object_id=str(instance.pk))
            }
            changes: list[AnnotationChange] = []
            for key in sorted(set(existing) | set(annotations)):
                row = existing.get(key)
                new_value = annotations.get(key)
                if row is None and new_value is not None:
                    self.create(content_type=content_type, object_id=str(instance.pk), key=key, value=new_value)
                    changes.append(AnnotationChange(key=key, old_value=None, new_value=new_value))
                elif row is not None and new_value is None:
                    row.delete()
                    changes.append(AnnotationChange(key=key, old_value=row.value, new_value=None))
                elif row is not None and new_value is not None and row.value != new_value:
                    changes.append(AnnotationChange(key=key, old_value=row.value, new_value=new_value))
                    row.value = new_value
                    row.save(update_fields=["value", "updated_at"])
        if changes:
            logger.debug(
                "%s.sync() %s changes to the annotations of %s %s",
                logger_prefix,
                len(changes),
                content_type.model,
                instance.pk,
            )
            dispatch_annotation_changes(instance, changes)
        return changes

    def delete_for_object(self, instance: models.Model) -> list[AnnotationChange]:
        """
        Delete a resource's annotations, when the resource itself is deleted.

        Handlers and the ``annotations_changed`` signal are sent the removals, with
        ``resource_deleted=True``.

        :param instance: The resource being deleted.
        :type instance: models.Model
        :returns: The removals.
        :rtype: list[AnnotationChange]
        """
        # pylint: disable=import-outside-toplevel
        from .handlers import dispatch_annotation_changes

        content_type = annotation_content_type(instance)
        rows = list(self.filter(content_type=content_type, object_id=str(instance.pk)).order_by("key"))
        if not rows:
            return []
        self.filter(pk__in=[row.pk for row in rows]).delete()
        changes = [AnnotationChange(key=row.key, old_value=row.value, new_value=None) for row in rows]
        dispatch_annotation_changes(instance, changes, resource_deleted=True)
        return changes


class AnnotationManager(models.Manager["Annotation"]):
    """
    The manager of :class:`Annotation`, whose queries are :class:`AnnotationQuerySet`.

    It declares the queryset's methods, so that type checkers know them on ``Annotation.objects``.
    """

    def get_queryset(self) -> AnnotationQuerySet:
        """Return an AnnotationQuerySet of every annotation."""
        return AnnotationQuerySet(self.model, using=self._db)

    def all(self) -> AnnotationQuerySet:
        """Return every annotation."""
        return self.get_queryset()

    def filter(self, *args, **kwargs) -> AnnotationQuerySet:
        """Return the annotations that match the filter."""
        return self.get_queryset().filter(*args, **kwargs)

    def exclude(self, *args, **kwargs) -> AnnotationQuerySet:
        """Return the annotations that don't match the filter."""
        return self.get_queryset().exclude(*args, **kwargs)

    def none(self) -> AnnotationQuerySet:
        """Return no annotations."""
        return self.get_queryset().none()

    def for_model(self, model: ModelOrInstance) -> AnnotationQuerySet:
        """See :meth:`AnnotationQuerySet.for_model`."""
        return self.get_queryset().for_model(model)

    def for_object(self, instance: models.Model) -> AnnotationQuerySet:
        """See :meth:`AnnotationQuerySet.for_object`."""
        return self.get_queryset().for_object(instance)

    def with_key(self, key: str, value: Optional[str] = None) -> AnnotationQuerySet:
        """See :meth:`AnnotationQuerySet.with_key`."""
        return self.get_queryset().with_key(key, value)

    def with_prefix(self, prefix: str) -> AnnotationQuerySet:
        """See :meth:`AnnotationQuerySet.with_prefix`."""
        return self.get_queryset().with_prefix(prefix)

    def sync(self, instance: models.Model, annotations: AnnotationsMap) -> list[AnnotationChange]:
        """See :meth:`AnnotationQuerySet.sync`."""
        return self.get_queryset().sync(instance, annotations)

    def delete_for_object(self, instance: models.Model) -> list[AnnotationChange]:
        """See :meth:`AnnotationQuerySet.delete_for_object`."""
        return self.get_queryset().delete_for_object(instance)


class Annotation(TimestampedModel):
    """
    One annotation of a Smarter resource: a key and a string value, as in Kubernetes.

    Read and write a resource's annotations through
    :attr:`smarter.lib.django.models.MetaDataModel.annotations`. Use this model directly to query
    annotations across resources.

    **Example:**

    .. code-block:: python

        from smarter.lib.annotation.models import Annotation

        # every Smarter resource of any kind that maps to CRM account A-10042
        Annotation.objects.with_key("acme.com/crm-account-id", "A-10042").resources()

        # every annotation that acme.com's integration owns
        Annotation.objects.with_prefix("acme.com")
    """

    # pylint: disable=missing-class-docstring
    class Meta:
        verbose_name = "Annotation"
        verbose_name_plural = "Annotations"
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id", "key"], name="annotation_unique_key_per_resource"
            ),
        ]
        indexes = [
            models.Index(fields=["content_type", "object_id"], name="annotation_resource_idx"),
            models.Index(fields=["key", "content_type"], name="annotation_key_idx"),
            models.Index(fields=["prefix"], name="annotation_prefix_idx"),
        ]

    objects: AnnotationManager = AnnotationManager()

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="+",
        help_text="The kind of the annotated resource: its root model.",
    )
    object_id = models.CharField(
        max_length=255,
        help_text="The primary key of the annotated resource, as a string: some resources' keys are strings.",
    )
    content_object = GenericForeignKey("content_type", "object_id")
    key = models.CharField(
        max_length=ANNOTATION_KEY_MAX_LENGTH,
        help_text="The annotation key, e.g. 'acme.com/crm-account-id': an optional DNS prefix, then a name.",
    )
    prefix = models.CharField(
        max_length=ANNOTATION_KEY_PREFIX_MAX_LENGTH,
        blank=True,
        default="",
        help_text="The key's prefix, e.g. 'acme.com', or empty when the key has none. Set from the key.",
    )
    value = models.TextField(blank=True, default="", help_text="The annotation value, a string.")

    def save(self, *args, **kwargs):
        """Set the prefix from the key, then save."""
        self.prefix = split_annotation_key(self.key)[0] or ""
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "prefix" not in update_fields:
            kwargs["update_fields"] = [*update_fields, "prefix"]
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.key}={self.value}"


__all__ = [
    "Annotation",
    "AnnotationManager",
    "AnnotationQuerySet",
    "annotation_content_type",
    "annotation_root_model",
    "get_cached_annotations",
    "prefetch_annotations",
]
