"""Django ORM base model"""

from functools import cached_property
from logging import getLogger
from typing import Optional

from django.db import models
from django.db.models.query import QuerySet
from taggit.managers import TaggableManager

from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.cache import cache_results
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.json import SmarterJSONEncoder
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .timestamped_model import TimestampedModel, validate_no_spaces

logger = getLogger(__name__)
cache_prefix = f"{__name__}."


# pylint: disable=W0613
def should_log_verbose(level):
    """Check if logging should be done based on the waffle switch."""
    return smarter_settings.verbose_logging


verbose_logger = WaffleSwitchedLoggerWrapper(logger, should_log_verbose)


class MetaDataModel(TimestampedModel):
    """
    Abstract base model that adds SAM metadata fields to a
    TimestampedModel Django ORM model. These are the
    the common fields that makeup the Pydantic SAM metadata model,
    along with timestamp fields for create/modify tracking.

    **Example Usage:**

    .. code-block:: python

        from smarter.smarter.lib.django.models import MetaDataModel
        from smarter.apps.account.models import User

        class MyModel(MetaDataModel):
            name = models.CharField(max_length=100)

    """

    # pylint: disable=missing-class-docstring
    class Meta:
        abstract = True

    name = models.CharField(
        max_length=255,
        help_text="Name in camelCase, e.g., 'apiKey', no special characters.",
        validators=[SmarterValidator.validate_snake_case, validate_no_spaces],
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
    annotations = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Key-value pairs for annotating this resource.",
        encoder=SmarterJSONEncoder,
    )

    def validate(self):
        """
        Validate the model.
        """
        super().validate()
        # version should be a semantic version: MAJOR.MINOR.PATCH
        if self.version and not SmarterValidator.is_valid_semantic_version(self.version):
            raise SmarterValueError(f"Version '{self.version}' is not a valid semantic version (MAJOR.MINOR.PATCH).")

    @cached_property
    def tags_list(self) -> list[str]:
        """
        Return the tags as a list of strings. We assume that @cached_property
        is more efficient at fetch that @cache_results, all things considered
        equal, which provides a marginal boost to instances. Meanwhile, the
        @cache_results is persisted to the Django cache, and thus outlives
        this instance. Thus, best of both worlds.

        :returns: List of tag names.
        :rtype: list[str]
        """

        # pylint: disable=W0613
        @cache_results(timeout=self.cache_expiration)
        def _get_tags_by_class_and_pk(cls_name: str, pk: int) -> list[str]:
            """
            Helper to cache tags retrieval.
            """
            verbose_logger.debug(
                "%s.tags_list - Retrieving tags for %s with pk=%d from database",
                self.formatted_class_name,
                cls_name,
                pk,
            )
            return [tag.name for tag in self.tags.all()]

        return _get_tags_by_class_and_pk(self.__class__.__name__, self.pk)

    @classmethod
    def get_cached_object(
        cls, *args, invalidate: Optional[bool] = False, pk: Optional[int] = None, name: Optional[str] = None, **kwargs
    ) -> Optional["MetaDataModel"]:
        """
        Retrieve a model instance by primary key or name, using caching to
        optimize performance. This method is selectively overridden in
        models that inherit from MetaDataModel to provide class-specific
        function parameters.

        Example usage:

        .. code-block:: python

            # Retrieve by primary key
            instance = MyModel.get_cached_object(pk=1)
            # Retrieve by name
            instance = MyModel.get_cached_object(name="exampleName")

        :param invalidate: Whether to invalidate the cache for this retrieval.
        :type invalidate: bool, optional
        :param pk: The primary key of the model instance to retrieve.
        :type pk: int, optional
        :param name: The name of the model instance to retrieve.
        :type name: str, optional

        :returns: The model instance if found, otherwise None.
        :rtype: Optional["MetaDataModel"]
        """
        logger_prefix = formatted_text(__name__ + "." + MetaDataModel.__name__ + ".get_cached_object()")
        verbose_logger.debug(
            "%s.get_cached_object() called with pk: %s, name: %s, invalidate: %s", logger_prefix, pk, name, invalidate
        )

        if cls._meta.abstract:
            raise NotImplementedError(
                "get_cached_object() must be called on a concrete model class, not an abstract base class."
            )

        if not pk and not name:
            return None

        @cache_results(timeout=cls.cache_expiration)
        def _get_object_by_name(name: str, class_name: str = cls.__name__) -> Optional["MetaDataModel"]:
            try:
                verbose_logger.debug(
                    "%s._get_object_by_name() cache miss for %s name: %s",
                    logger_prefix,
                    class_name,
                    name,
                )
                return cls.objects.prefetch_related("tags").get(name=name)
            except cls.DoesNotExist:
                verbose_logger.debug(
                    "%s._get_object_by_name() no %s object found for name: %s",
                    logger_prefix,
                    class_name,
                    name,
                )
                return None
            except cls.MultipleObjectsReturned as e:
                logger.error(
                    "%s.get_cached_object() - Multiple %s objects found for name '%s'. Returning the first one.",
                    logger_prefix,
                    class_name,
                    name,
                )
                raise SmarterValueError(f"Multiple {class_name} objects found for name '{name}'.") from e

        if invalidate:
            _get_object_by_name.invalidate(name, cls.__name__)

        if name:
            return _get_object_by_name(name)

        return super().get_cached_object(*args, invalidate=invalidate, pk=pk, **kwargs)  # type: ignore[return-value]

    @classmethod
    def get_cached_objects(cls, invalidate: Optional[bool] = False) -> QuerySet["MetaDataModel"]:
        """
        Retrieve model instances using caching to optimize performance.
        This method is selectively overridden in models that inherit from
        MetaDataModel to provide class-specific function parameters.

        Example usage:

        .. code-block:: python

            # Retrieve all instances
            instances = MyModel.get_cached_objects()

        :param invalidate: Whether to invalidate the cache for this retrieval.
        :type invalidate: bool
        :returns: A queryset of all model instances.
        :rtype: QuerySet
        """
        logger_prefix = formatted_text(__name__ + "." + cls.__name__ + ".get_cached_objects()")
        verbose_logger.debug(
            "%s.get_cached_objects() called for %s with invalidate=%s", logger_prefix, cls.__name__, invalidate
        )

        if cls._meta.abstract:
            raise NotImplementedError(
                "get_cached_object() must be called on a concrete model class, not an abstract base class."
            )

        if invalidate:
            pass

        return super().get_cached_objects(invalidate=invalidate)  # type: ignore

    def save(self, *args, **kwargs):
        """
        Save the model instance to the database, performing validation before the actual save.

        This method overrides the default ``save()`` behavior of Django models to ensure that
        the model is validated by calling :meth:`validate` before any data is written to the database.
        If validation fails, a :exc:`django.core.exceptions.ValidationError` is raised with detailed
        information about the error, the arguments passed, the model class, and the current field values.

        Parameters
        ----------
        *args
            Positional arguments passed to the parent ``save()`` method. These are forwarded to Django's ORM.
        **kwargs
            Keyword arguments passed to the parent ``save()`` method. These are forwarded to Django's ORM.

        Examples
        --------
        .. code-block:: python

            obj = MyModel(name="Example")
            obj.save()  # Will call validate() before saving
        .. note::

            - The :meth:`validate` method is intended to be overridden in subclasses to provide custom validation logic.
            - If :meth:`validate` raises a :exc:`ValidationError`, the save operation is aborted and the error is propagated.
            - The error message includes the arguments, keyword arguments, model class, and current field values for easier debugging.
        .. important::

            - If you override this method in a subclass, always call ``super().save(*args, **kwargs)`` to retain validation and timestamp functionality.
            - If validation fails, no data will be saved to the database.
        """
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if not is_new and type(self).__bases__[0] == MetaDataModel:
            self.__class__.get_cached_object(invalidate=True, pk=self.pk)  # type: ignore
            self.__class__.get_cached_object(invalidate=True, name=self.name)  # type: ignore
            self.__class__.get_cached_objects(invalidate=True)  # type: ignore

    def __str__(self):
        return f"{self.pk} {self.name}"

    def __repr__(self):
        return f"<{self.__class__.__name__} id={getattr(self, 'id', None)} name={self.name} created_at={self.created_at} updated_at={self.updated_at}>"


__all__ = ["MetaDataModel"]
