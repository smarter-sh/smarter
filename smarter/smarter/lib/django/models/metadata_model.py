"""The abstract base model of Smarter models that hold SAM metadata: name, description, version, tags, annotations."""

from collections.abc import Collection
from functools import cached_property
from logging import getLogger
from typing import Any, Optional, Self

from cache_results import cache_results
from django.apps import apps
from django.db import models
from django.db.models.query import QuerySet
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from taggit.managers import TaggableManager

from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.common.utils import rfc1034_compliant_str
from smarter.lib.annotation.validation import (
    AnnotationsInput,
    AnnotationsMap,
    normalize_annotations,
)
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .timestamped_model import TimestampedModel, should_log_verbose

logger = getLogger(__name__)
logger_prefix = SmarterFormattedText.text(__name__)
cache_prefix = f"{__name__}."


verbose_logger = WaffleSwitchedLoggerWrapper(logger, should_log_verbose)


@cache_results(timeout=smarter_settings.cache_expiration)
def _get_tags_by_model_and_pk(model_label: str, pk: int) -> list[str]:
    """
    Return the tag names of a MetaDataModel instance, cached for ``smarter_settings.cache_expiration``.

    :func:`tags_changed` invalidates it.

    :param model_label: The model's label, e.g. ``llmclient.LLMClient``.
    :param pk: The instance's primary key.
    :returns: The names of the instance's tags.
    """
    model = apps.get_model(model_label)
    instance = model.objects.get(pk=pk)
    retval = [tag.name for tag in instance.tags.all()]
    verbose_logger.debug(
        "%s._get_tags_by_model_and_pk() fetched and cached tags for %s with pk=%s from database",
        logger_prefix,
        model_label,
        pk,
    )
    return retval


class MetaDataModel(TimestampedModel):
    """
    Abstract base model that adds the SAM metadata fields to :class:`TimestampedModel`.

    These are the common fields that make up the Pydantic SAM metadata model, along with the
    timestamp fields for create/modify tracking.

    **Example Usage:**

    .. code-block:: python

        from smarter.lib.django.models import MetaDataModel

        class MyModel(MetaDataModel):
            name = models.CharField(max_length=100)
    """

    # pylint: disable=missing-class-docstring
    class Meta:
        abstract = True

    name = models.CharField(
        max_length=255,
        help_text="Name in camelCase, e.g., 'apiKey', no special characters.",
        validators=[SmarterValidator.validate_snake_case, SmarterValidator.validate_no_spaces],
    )
    description = models.TextField(
        help_text="A brief description of this resource. Be verbose, but not too verbose.",
        blank=True,
        null=True,
        default="",
    )
    version = models.CharField(
        max_length=255,
        default="1.0.0",
        help_text="Semantic version in the format MAJOR.MINOR.PATCH, e.g., '1.0.0'.",
        blank=True,
        null=True,
    )
    tags = TaggableManager(
        blank=True,
        help_text="Tags for categorizing and organizing this resource.",
    )

    _pending_annotations: Optional[AnnotationsMap] = None
    """Annotations assigned to the instance, and written to the database by the next ``save()``."""

    _prefetched_annotations: Optional[AnnotationsMap] = None
    """Annotations read for a whole list of resources by :func:`smarter.lib.annotation.models.prefetch_annotations`."""

    _loaded_name: Optional[str] = None
    """The name the row had when it was loaded or last saved, so that :meth:`save` can invalidate it after a rename."""

    @property
    def annotations(self) -> AnnotationsMap:
        """
        The resource's annotations: a map of string keys to string values, as in Kubernetes.

        Assigning to it validates the new annotations, and the next ``save()`` makes the stored
        annotations exactly these, adding, changing and removing rows of
        :class:`smarter.lib.annotation.models.Annotation`. Assignment accepts a map, or the list of
        one-key maps of older manifests, and converts scalar values to strings.

        **Example:**

        .. code-block:: python

            llmclient.annotations = {**llmclient.annotations, "acme.com/crm-account-id": "A-10042"}
            llmclient.save()

        :returns: A copy of the annotations. Changing it doesn't change the resource.
        """
        if self._pending_annotations is not None:
            return dict(self._pending_annotations)
        if self._prefetched_annotations is not None:
            return dict(self._prefetched_annotations)
        if self.pk is None:
            return {}
        # pylint: disable=import-outside-toplevel
        from smarter.lib.annotation.models import (
            annotation_content_type,
            get_cached_annotations,
        )

        return dict(get_cached_annotations(annotation_content_type(self).pk, str(self.pk)))

    @annotations.setter
    def annotations(self, value: AnnotationsInput) -> None:
        """Validate the annotations, and keep them for the next ``save()``."""
        self._pending_annotations = normalize_annotations(value)
        self._prefetched_annotations = None

    def set_annotation(self, key: str, value: object) -> None:
        """
        Add or change one annotation of a saved resource, immediately.

        :param key: The annotation key, e.g. ``acme.com/crm-account-id``.
        :param value: The value. Scalars are converted to strings.
        :raises SmarterAnnotationError: If the key or value is invalid.
        """
        self.annotations = {**self.annotations, key: value}
        self.save_annotations()

    def remove_annotation(self, key: str) -> None:
        """
        Remove one annotation of a saved resource, immediately.

        Does nothing if it doesn't exist.

        :param key: The annotation key.
        """
        annotations = self.annotations
        if key in annotations:
            annotations.pop(key)
            self.annotations = annotations
            self.save_annotations()

    def save_annotations(self) -> None:
        """Write annotations assigned since the last ``save()`` to the database, without saving the resource's other fields."""
        if self._pending_annotations is None or self.pk is None:
            return
        # pylint: disable=import-outside-toplevel
        from smarter.lib.annotation.models import Annotation

        pending = self._pending_annotations
        self._pending_annotations = None
        Annotation.objects.sync(self, pending)

    @classmethod
    def with_annotation(cls, key: str, value: Optional[str] = None) -> QuerySet:
        """
        Return the resources of this model that have the annotation ``key``, with ``value`` if given.

        **Example:**

        .. code-block:: python

            LLMClient.with_annotation("acme.com/crm-account-id", "A-10042")

        :param key: The annotation key.
        :param value: The value to match, or ``None`` for any value.
        :returns: The resources, not filtered by any user's permissions.
        """
        # pylint: disable=import-outside-toplevel
        from smarter.lib.annotation.selectors import model_with_annotation

        return model_with_annotation(cls, key, value)

    def validate(self):
        """
        Validate the model: its version, when set, must be a semantic version.

        :raises SmarterValueError: if the version is not ``MAJOR.MINOR.PATCH``.
        """
        super().validate()
        # version should be a semantic version: MAJOR.MINOR.PATCH
        if self.version and not SmarterValidator.is_valid_semantic_version(self.version):
            raise SmarterValueError(f"Version '{self.version}' is not a valid semantic version (MAJOR.MINOR.PATCH).")

    def clone(self, new_name: str, new_version: Optional[str] = None) -> "MetaDataModel":
        """
        Clone the model instance with a new name and optional new version.

        Only the name, version, description and annotations are copied. The clone is validated
        and saved.

        :param new_name: The name for the cloned instance.
        :param new_version: The version for the cloned instance. If not provided, it will be the same as the original.
        :returns: The new, saved instance.
        """
        clone_kwargs = {
            "name": new_name,
            "version": new_version if new_version is not None else self.version,
            "description": self.description,
            "annotations": self.annotations,
        }
        clone_instance = self.__class__(**clone_kwargs)
        clone_instance.full_clean()  # Validate the cloned instance
        clone_instance.save()  # Save the new instance to the database
        return clone_instance

    def rename(self, new_name: str) -> "MetaDataModel":
        """
        Rename the model instance with a new name.

        The instance is validated and saved.

        :param new_name: The new name for the instance.
        :returns: The updated instance of MetaDataModel with the new name.
        """
        self.name = new_name
        self.full_clean()  # Validate the updated instance
        self.save()  # Save the changes to the database
        return self

    @cached_property
    def ready(self) -> bool:
        """
        Check if the model instance is ready for use.

        :returns: True if the instance is ready, False otherwise.
        """
        return super().ready and self.name is not None

    @cached_property
    def rfc1034_compliant_name(self) -> Optional[str]:
        """
        Returns a URL-friendly name for the llmclient.

        This property returns an RFC 1034-compliant name for the llmclient, suitable for use in URLs and DNS labels.

        **Example:**

        .. code-block:: python

            self.name = 'Example LLMClient 1'
            self.rfc1034_compliant_name  # 'example-llmclient-1'

        :returns: The RFC 1034-compliant name, or None if ``self.name`` is not set.
        """
        if self.name:
            return rfc1034_compliant_str(self.name)
        return None

    @cached_property
    def tags_list(self) -> list[str]:
        """
        Return the tags as a list of strings.

        It is cached twice: ``cached_property`` keeps it on the instance, which is the fastest
        lookup, and ``cache_results`` keeps it in the Django cache, which outlives the instance.

        :returns: List of tag names.
        """
        return _get_tags_by_model_and_pk(self._meta.label, self.pk)

    @classmethod
    def get_cached_object(
        cls, *args, invalidate: Optional[bool] = False, pk: Optional[int] = None, name: Optional[str] = None, **kwargs
    ) -> "MetaDataModel":
        """
        Retrieve a model instance by primary key or name, using caching to optimize performance.

        This method is selectively overridden in models that inherit from MetaDataModel to provide class-specific
        function parameters.

        **Example**

        .. code-block:: python

            # Retrieve by primary key
            instance = MyModel.get_cached_object(pk=1)
            # Retrieve by name
            instance = MyModel.get_cached_object(name="exampleName")

        :param args: Accepted for the subclasses' signature, and ignored.
        :param invalidate: Whether to drop the cached row, and read it again from the database.
        :param pk: The primary key of the model instance to retrieve.
        :param name: The name of the model instance to retrieve, which takes precedence over ``pk``.
        :param kwargs: Passed on to :meth:`TimestampedModel.get_cached_object` for a lookup by pk.
        :returns: The model instance.
        :raises NotImplementedError: if called on an abstract model class.
        :raises ~django.core.exceptions.ObjectDoesNotExist: the model's ``DoesNotExist``, if neither
            ``pk`` nor ``name`` is given, or no row matches.
        :raises ~django.core.exceptions.MultipleObjectsReturned: the model's
            ``MultipleObjectsReturned``, if several rows have the name.
        """
        class_prefix = SmarterFormattedText.text(__name__ + "." + MetaDataModel.__name__)

        if cls._meta.abstract:
            raise NotImplementedError(
                "get_cached_object() must be called on a concrete model class, not an abstract base class."
            )

        if not pk and not name:
            raise cls.DoesNotExist(f"Must provide either 'pk' or 'name' to retrieve a {cls.__name__} object.")

        @cache_results(timeout=cls.cache_expiration)
        def _get_object_by_name(name: str, class_name: str = cls.__name__) -> "MetaDataModel":
            try:
                verbose_logger.debug(
                    "%s._get_object_by_name() called with pk: %s, name: %s, invalidate: %s",
                    class_prefix,
                    pk,
                    name,
                    invalidate,
                )
                # taggit has no type information, so django-stubs doesn't know that tags is a relation.
                retval = cls._default_manager.prefetch_related("tags").get(name=name)  # type: ignore[misc]
                verbose_logger.debug(
                    "%s._get_object_by_name() fetched and cached %s name: %s",
                    class_prefix,
                    class_name,
                    name,
                )
                return retval
            except cls.DoesNotExist as e:
                verbose_logger.debug(
                    "%s._get_object_by_name() no %s object found for name: %s",
                    class_prefix,
                    class_name,
                    name,
                )
                raise cls.DoesNotExist(f"{class_name} object with name '{name}' does not exist.") from e
            except cls.MultipleObjectsReturned as e:
                logger.error(
                    "%s._get_object_by_name() - Multiple %s objects found for name '%s'.",
                    class_prefix,
                    class_name,
                    name,
                )
                raise cls.MultipleObjectsReturned(f"Multiple {class_name} objects found for name '{name}'.") from e

        if invalidate:
            _get_object_by_name.invalidate(name, cls.__name__)

        if name:
            # same args as invalidate() above, so that both produce the same cache key
            return _get_object_by_name(name, cls.__name__)

        # TimestampedModel.get_cached_object() takes no positional arguments after cls.
        return super().get_cached_object(invalidate=invalidate, pk=pk, **kwargs)  # type: ignore[return-value]

    @classmethod
    def get_cached_objects(cls, invalidate: Optional[bool] = False, **kwargs) -> QuerySet["MetaDataModel"]:
        """
        Retrieve model instances using caching to optimize performance.

        This method is selectively overridden in models that inherit from
        MetaDataModel to provide class-specific function parameters.

        **Example**

        .. code-block:: python

            # Retrieve all instances
            instances = MyModel.get_cached_objects()

        :param invalidate: Whether to invalidate the cache for this retrieval.
        :param kwargs: Passed on to :meth:`TimestampedModel.get_cached_objects`.
        :returns: A queryset of all model instances.
        :raises NotImplementedError: if called on an abstract model class.
        """
        class_prefix = SmarterFormattedText.text(__name__ + "." + cls.__name__)
        verbose_logger.debug(
            "%s.get_cached_objects() called for %s with invalidate=%s", class_prefix, cls.__name__, invalidate
        )

        if cls._meta.abstract:
            raise NotImplementedError(
                "get_cached_objects() must be called on a concrete model class, not an abstract base class."
            )

        return super().get_cached_objects(invalidate=invalidate, **kwargs)  # type: ignore

    def save(self, *args, **kwargs):
        """
        Validate and save the model instance, write its pending annotations, and invalidate its caches.

        :meth:`TimestampedModel.save` validates the instance first. Then the annotations assigned
        since the last save are written. When an existing row of a direct subclass of
        MetaDataModel is saved, its cached copies, by pk and by name, and the cached list of all
        rows, are invalidated.

        **Example**

        .. code-block:: python

            obj = MyModel(name="Example")
            obj.save()  # Will call validate() before saving

        .. important::

            - If you override this method in a subclass, always call ``super().save(*args, **kwargs)`` to retain validation and timestamp functionality.
            - If validation fails, no data will be saved to the database.

        :param args: Positional arguments, forwarded to Django's ``save()``.
        :param kwargs: Keyword arguments, forwarded to Django's ``save()``.
        :raises SmarterValueError: if validation fails.
        """
        is_new = self.pk is None
        super().save(*args, **kwargs)
        self.save_annotations()
        if not is_new and type(self).__bases__[0] == MetaDataModel:
            self.__class__.get_cached_object(invalidate=True, pk=self.pk)  # type: ignore
            # a blank name, e.g. a UserProfile created by the oauth pipeline, was never cached by name,
            # and get_cached_object() refuses to look one up.
            if self.name:
                self.__class__.get_cached_object(invalidate=True, name=self.name)  # type: ignore
            # a rename leaves the old name's cached copy behind, which would still return this row.
            loaded_name = self._loaded_name
            if loaded_name and loaded_name != self.name:
                self.invalidate_cached_name(loaded_name)
        self._loaded_name = self.name

    @classmethod
    def from_db(cls, db: Optional[str], field_names: Collection[str], values: Collection[Any], **kwargs: Any) -> Self:
        """
        Load a row, and remember its name, so that :meth:`save` can tell a rename.

        :param db: The database alias.
        :param field_names: The loaded fields' names.
        :param values: The loaded fields' values.
        :param kwargs: Passed on to Django's, e.g. the ``fetch_mode`` that Django's type stubs already declare.
        :returns: The instance.
        """
        instance = super().from_db(db, field_names, values, **kwargs)
        # a deferred name is not loaded, and is not read here, which would query it.
        instance._loaded_name = instance.__dict__.get("name")
        return instance

    @classmethod
    def invalidate_cached_name(cls, name: str) -> None:
        """
        Drop the cached copy of the row that had ``name``, without reading anything.

        :meth:`get_cached_object` with ``invalidate=True`` would look the name up again, and a
        renamed row no longer has it.

        :param name: The name the row was cached by.
        """
        try:
            cls.get_cached_object(invalidate=True, name=name)  # type: ignore
        except cls.DoesNotExist:
            pass

    def __str__(self) -> str:
        """
        Return the instance's pk and name, e.g. ``1 example``.

        :returns: The short description of the row.
        """
        return f"{self.pk} {self.name}"

    def __repr__(self) -> str:
        """
        Return the model's class name, pk, name and timestamps, for debugging.

        :returns: The description of the row.
        """
        return f"<{self.__class__.__name__} pk={self.pk} name={self.name} created_at={self.created_at} updated_at={self.updated_at}>"


__all__ = ["MetaDataModel"]


# pylint: disable=W0613
@receiver(m2m_changed)
def tags_changed(sender, instance, action, **kwargs):
    """
    Invalidate tags_list when the tags of a MetaDataModel instance change.

    :param sender: The m2m through model.
    :param instance: The instance whose many-to-many relation changed.
    :param action: The m2m_changed action; only ``post_add``, ``post_remove`` and ``post_clear`` act.
    :param kwargs: The rest of the signal's arguments.
    """
    if action not in ("post_add", "post_remove", "post_clear"):
        return
    if not isinstance(instance, MetaDataModel):
        return
    if not instance.pk:
        return
    # the instance's own dict, where cached_property stores tags_list. vars() is typed as a dict.
    vars(instance).pop("tags_list", None)
    # pylint: disable=W0212
    _get_tags_by_model_and_pk.invalidate(instance._meta.label, instance.pk)
