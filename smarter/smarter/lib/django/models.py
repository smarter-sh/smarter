"""Django ORM base model"""

import base64
import datetime
import json
import re
from functools import cached_property
from logging import getLogger
from typing import Any, Optional

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.query import QuerySet
from django.forms.models import model_to_dict
from django.utils.timezone import is_aware, make_aware
from taggit.managers import TaggableManager

from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.mixins import SmarterHelperMixin
from smarter.lib.cache import cache_results
from smarter.lib.cache import lazy_cache as cache
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.json import SmarterJSONEncoder

logger = getLogger(__name__)
cache_prefix = f"{__name__}."


def validate_no_spaces(value) -> None:
    """Validate that the string does not contain spaces."""
    if " " in value:
        raise SmarterValueError(f"Value must not contain spaces: {value}")


class TimestampedModel(models.Model, SmarterHelperMixin):
    """
    Abstract base model for all Django ORM models in the Smarter project, providing automatic
    timestamp fields and utility methods.

    This class should be used as the base class for all models in the project to ensure
    consistent tracking of creation and modification times. It adds ``created_at`` and
    ``updated_at`` fields, and provides validation and time-difference utilities.

    **Example Usage:**

    .. code-block:: python

        from smarter.smarter.lib.django.models import TimestampedModel

        class MyModel(TimestampedModel):
            name = models.CharField(max_length=100)

        # Creating an instance
        obj = MyModel.objects.create(name="Example")
        print(obj.created_at)  # Timestamp of creation
        print(obj.updated_at)  # Timestamp of last update

        # Checking elapsed time since last update
        seconds = obj.elapsed_updated()
        print(f"Seconds since last update: {seconds}")

    **Parameters:**

    Inherits all parameters from ``django.db.models.Model``.

    .. note::

        - This class is abstract and will not create a database table by itself.
        - The ``validate()`` method is a stub and should be implemented in subclasses as needed.
        - The ``save()`` method enforces validation before saving, raising a detailed error if validation fails.

    .. important::

        - If you override ``save()``, ensure you call ``super().save(*args, **kwargs)`` to retain validation and timestamp behavior.
        - The ``elapsed_updated`` property expects ``updated_at`` to be set; if not, it returns ``None``.
        - Passing a non-datetime object to ``elapsed_updated`` will raise a ``TypeError``.
        - The hashed ID methods provide a way to encode and decode object IDs for use in URLs
          in cases where you want to avoid exposing raw database IDs.

    """

    HASH_PREFIX = "r"
    HASH_SUFFIX = "x"
    HASH_FLOOR = 1000000
    _hash_regex = None
    cache_expiration = 60  # 60 seconds

    created_at = models.DateTimeField(auto_now_add=True, null=True, editable=False, db_index=True)
    """
    Timestamp indicating when the model instance was created.
    This field is automatically set to the current date and time when the instance is first created.
    It is indexed in the database for efficient querying.
    """
    updated_at = models.DateTimeField(auto_now=True, null=True, editable=False, db_index=True)
    """
    Timestamp indicating when the model instance was last updated.
    This field is automatically updated to the current date and time whenever the instance is saved.
    It is indexed in the database for efficient querying.
    """

    # pylint: disable=missing-class-docstring
    class Meta:
        abstract = True

    def validate(self):
        """
        Validate the model.

        .. attention::

            Intended to be overridden in subclasses to provide custom validation logic.

        """

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
        try:
            self.validate()
        except (ValidationError, SmarterValueError) as e:
            raise SmarterValueError(
                f"TimestampedModel().save() validation error: {e} | args={args} kwargs={kwargs} | model={self.__class__.__name__} | field_values={self.__dict__}"
            ) from e
        except Exception as e:
            raise SmarterValueError(
                f"TimestampedModel().save() unexpected error during validation: {e} | args={args} kwargs={kwargs} | model={self.__class__.__name__} | field_values={self.__dict__}"
            ) from e
        super().save(*args, **kwargs)

    @classmethod
    def hash_regex(cls) -> re.Pattern:
        """
        Returns a regex pattern that matches the hashed ID format for this model anywhere in a string.

        The hashed ID format is defined by the ``HASH_PREFIX`` and ``HASH_SUFFIX`` class attributes,
        with a base64-encoded string in between. This regex can be used to validate or extract
        hashed IDs from strings, including when embedded in URLs.

        :returns: A regex pattern for matching hashed IDs.
        :rtype: re.Pattern
        """
        if cls._hash_regex is None:
            cls._hash_regex = re.compile(f"{cls.HASH_PREFIX}[A-Za-z0-9_-]+{cls.HASH_SUFFIX}")
        return cls._hash_regex

    @cached_property
    def hashed_id(self) -> str:
        """
        Returns a URL-friendly hashed version of the object's ID for use in URLs and other
        contexts where an obscured, non-identifying, non-sequential identifier is preferred.

        :returns: Hashed ID string (URL-safe, no padding)
        :rtype: str
        """
        id_value = int(self.id) + self.HASH_FLOOR
        encoded = base64.urlsafe_b64encode(str(id_value).encode()).decode().rstrip("=")
        return self.HASH_PREFIX + encoded + self.HASH_SUFFIX

    @classmethod
    def id_from_hashed_id(cls, hashed_id: str) -> Optional[int]:
        """
        Decodes a hashed ID back to the original object ID.

        :param hashed_id: The hashed ID string to decode (URL-safe, no padding).
        :returns: The original object ID if decoding is successful, otherwise None.
        :rtype: Optional[int]
        """

        cache_key = f"{cache_prefix}id_from_hashed_id:{hashed_id}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        try:
            logger.debug(
                "%s.id_from_hashed_id() - Attempting to decode hashed_id: %s",
                cls.formatted_class_name,
                hashed_id,
            )
            if not hashed_id.startswith(cls.HASH_PREFIX) or not hashed_id.endswith(cls.HASH_SUFFIX):
                return None
            encoded_str = hashed_id[len(cls.HASH_PREFIX) : -len(cls.HASH_SUFFIX)]
            # Add padding if needed
            padding = "=" * (-len(encoded_str) % 4)
            encoded_str += padding
            decoded_bytes = base64.urlsafe_b64decode(encoded_str.encode())
            decoded_str = decoded_bytes.decode()
            retval = int(decoded_str) - cls.HASH_FLOOR
            logger.debug(
                "%s.id_from_hashed_id() - Successfully decoded hashed_id: %s to id: %d",
                cls.formatted_class_name,
                hashed_id,
                retval,
            )
            cache.set(cache_key, retval)
            return retval
        except (base64.binascii.Error, ValueError) as e:
            logger.error(
                "%s.id_from_hashed_id() - Failed to decode hashed_id '%s': %s",
                cls.formatted_class_name,
                hashed_id,
                e,
            )
            return None
        # pylint: disable=broad-except
        except Exception as e:
            logger.exception(
                "%s.id_from_hashed_id() - Unexpected error while decoding hashed_id '%s': %s",
                cls.formatted_class_name,
                hashed_id,
                e,
            )
            return None

    @classmethod
    def find_hash(cls, value: str) -> Optional[str]:
        """
        Finds and returns the first substring in the given value that matches
        the hashed ID format.

        :param value: The string to search for a hashed ID.
        :returns: The first matching hashed ID if found, otherwise None.
        :rtype: Optional[str]
        """
        logger.debug(
            "%s.find_hash() - Searching for hashed ID in value: %s",
            cls.formatted_class_name,
            value,
        )
        pattern = cls.hash_regex()
        match = pattern.search(value)
        retval = match.group(0) if match else None
        if retval:
            logger.debug(
                "%s.find_hash() - Found hashed ID: %s",
                cls.formatted_class_name,
                retval,
            )
        else:
            logger.debug(
                "%s.find_hash() - No hashed ID found in value: %s",
                cls.formatted_class_name,
                value,
            )
        return retval

    @property
    def elapsed_updated(self, dt=None) -> Optional[int]:
        """
        Calculate the absolute time difference in seconds between a given datetime and the model's ``updated_at`` timestamp.

        This property is useful for determining how much time has elapsed since the model instance was last updated,
        or for comparing the ``updated_at`` field to any arbitrary datetime.

        **Parameters:**

        - dt (datetime, optional):
          The reference datetime to compare against ``updated_at``.
          - If ``dt`` is not provided, the current time is used.
          - Both naive and timezone-aware datetime objects are supported; the method will handle conversions as needed.

        **Returns:**

        - int or None:
          The absolute difference in seconds between ``updated_at`` and ``dt``.
          Returns ``None`` if ``updated_at`` is not set.

        **Example Usage:**

        .. code-block:: python

            obj = MyModel.objects.get(pk=1)
            # Time since last update
            seconds = obj.elapsed_updated
            print(f"Seconds since last update: {seconds}")

            # Compare to a specific datetime
            import datetime
            dt = datetime.datetime(2025, 12, 1, 12, 0, 0)
            diff = obj.elapsed_updated(dt)
            print(f"Seconds between updated_at and 2025-12-01 12:00:00: {diff}")

        .. note::

            - Handles both naive and aware datetime objects, converting as necessary to ensure accurate calculation.
            - If ``updated_at`` is not set (e.g., the object has not been saved), returns ``None``.

        .. attention::

            - If ``dt`` is provided and is not a ``datetime.datetime`` instance, a ``TypeError`` will be raised.
            - Always ensure that ``updated_at`` is set before relying on this property for calculations.

        """
        utc = datetime.timezone.utc
        if not self.updated_at:
            return None

        if dt is None:
            dt = datetime.datetime.now(utc) if is_aware(self.updated_at) else datetime.datetime.now()
        if not isinstance(dt, datetime.datetime):
            raise TypeError(f"Expected a datetime object, got {type(dt)} instead.")

        updated = self.updated_at
        if is_aware(updated) and not is_aware(dt):
            dt = make_aware(dt, utc)
        elif not is_aware(updated) and is_aware(dt):
            updated = make_aware(updated, utc)

        delta = int(abs((updated - dt).total_seconds()))
        return delta

    def to_json(self) -> dict[str, Any]:
        """
        Serialize the model instance to a JSON-compatible dictionary.

        This method uses the custom ``SmarterJSONEncoder`` to ensure that all fields,
        including timestamps and any complex data types, are properly serialized.

        :returns: A dictionary representation of the model instance suitable for JSON serialization.
        :rtype: dict[str, Any]
        """

        data = model_to_dict(self)
        retval = json.loads(json.dumps(data, cls=SmarterJSONEncoder))
        return retval

    @classmethod
    def get_cached_object(cls, pk: int, invalidate: Optional[bool] = False) -> Optional[models.Model]:
        """
        Retrieve a model instance by primary key, using caching to
        optimize performance. This method is selectively overridden in
        models that inherit from TimestampedModel to provide class-specific
        function parameters.

        Example usage:

        .. code-block:: python

            # Retrieve by primary key
            instance = MyModel.get_cached_object(pk=1)

        :param pk: The primary key of the model instance to retrieve.
        :returns: The model instance if found, otherwise None.
        :rtype: Optional[models.Model]
        """
        logger_prefix = formatted_text(__name__ + "." + cls.__name__ + ".get_cached_object()")
        logger.debug("%s.get_cached_object() called with pk: %s", logger_prefix, pk)

        if cls._meta.abstract:
            raise NotImplementedError(
                "get_cached_object() must be called on a concrete model class, not an abstract base class."
            )

        if not pk:
            return None

        @cache_results(timeout=cls.cache_expiration)
        def _get_model_by_pk(pk: int) -> Optional[models.Model]:

            try:
                return cls.objects.get(pk=pk)
            except cls.DoesNotExist:
                return None

        if invalidate:
            _get_model_by_pk.invalidate(pk)

        return _get_model_by_pk(pk)

    @classmethod
    def get_cached_objects(cls, invalidate: Optional[bool] = False) -> QuerySet["TimestampedModel"]:
        """
        Retrieve model instances using caching to optimize performance.
        This method is selectively overridden in models that inherit from
        TimestampedModel to provide class-specific function parameters.

        Example usage:

        .. code-block:: python

            # Retrieve all instances
            instances = MyModel.get_cached_objects()

        :returns: A queryset of all model instances.
        :rtype: QuerySet
        """
        logger_prefix = formatted_text(__name__ + "." + cls.__name__ + ".get_cached_objects()")
        logger.debug("%s.get_cached_objects() called", logger_prefix)

        if cls._meta.abstract:
            raise NotImplementedError(
                "get_cached_object() must be called on a concrete model class, not an abstract base class."
            )

        @cache_results(timeout=cls.cache_expiration)
        def _get_all_models() -> QuerySet["TimestampedModel"]:
            return cls.objects.all()

        if invalidate:
            _get_all_models.invalidate()

        return _get_all_models()

    def __str__(self):
        return f"{self.__class__.__name__}(id={getattr(self, 'id', None)})"

    def __repr__(self):
        return f"<{self.__class__.__name__} id={getattr(self, 'id', None)} created_at={self.created_at} updated_at={self.updated_at}>"


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
            logger.debug(
                "%s.tags_list - Retrieving tags for %s with pk=%d from database",
                self.formatted_class_name,
                cls_name,
                pk,
            )
            return [tag.name for tag in self.tags.all()]

        return _get_tags_by_class_and_pk(self.__class__.__name__, self.pk)

    @classmethod
    def get_cached_object(
        cls, pk: Optional[int] = None, name: Optional[str] = None, invalidate: Optional[bool] = False
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

        :param pk: The primary key of the model instance to retrieve.
        :param name: The name of the model instance to retrieve.
        :returns: The model instance if found, otherwise None.
        :rtype: Optional["MetaDataModel"]
        """
        logger_prefix = formatted_text(__name__ + "." + cls.__name__ + ".get_cached_object()")
        logger.debug("%s.get_cached_object() called with pk: %s, name: %s", logger_prefix, pk, name)

        if cls._meta.abstract:
            raise NotImplementedError(
                "get_cached_object() must be called on a concrete model class, not an abstract base class."
            )

        if not pk and not name:
            return None

        @cache_results(timeout=cls.cache_expiration)
        def _get_object_by_name(name: str) -> Optional["MetaDataModel"]:
            try:
                return cls.objects.prefetch_related("tags").get(name=name)
            except cls.DoesNotExist:
                return None
            except cls.MultipleObjectsReturned as e:
                logger.error(
                    "%s.get_cached_object() - Multiple objects found with name '%s'. Returning the first one.",
                    cls.formatted_class_name,
                    name,
                )
                raise SmarterValueError(f"Multiple objects found with name '{name}'.") from e

        if invalidate:
            _get_object_by_name.invalidate(name)

        if name:
            return _get_object_by_name(name)

        return super().get_cached_object(pk=pk, invalidate=invalidate)  # type: ignore[return-value]

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

        :returns: A queryset of all model instances.
        :rtype: QuerySet
        """
        logger_prefix = formatted_text(__name__ + "." + cls.__name__ + ".get_cached_objects()")
        logger.debug("%s.get_cached_objects() called", logger_prefix)

        if cls._meta.abstract:
            raise NotImplementedError(
                "get_cached_object() must be called on a concrete model class, not an abstract base class."
            )

        if invalidate:
            pass

        return super().get_cached_objects(invalidate=invalidate)  # type: ignore
