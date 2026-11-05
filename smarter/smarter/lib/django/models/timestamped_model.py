"""The abstract base model of every Smarter Django model, with timestamps, hashed ids and caching."""

import base64
import datetime
import json
import re
from functools import cached_property
from typing import ClassVar, Optional

from cache_results import cache_results
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.query import QuerySet
from django.forms.models import model_to_dict
from django.utils.timezone import is_aware, make_aware

from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.common.mixins import SmarterHelperMixin
from smarter.lib import logging
from smarter.lib.json import SmarterJSONEncoder, to_jsonable
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.typing import SmarterDictType

logger = logging.getSmarterLogger(__name__)
cache_prefix = f"{__name__}."


# pylint: disable=W0613
def should_log_verbose(level: int) -> bool:
    """
    Return whether verbose logging is on, from the ``smarter_settings.verbose_logging`` setting.

    :param level: The log level of the message, which is ignored.
    :returns: True if verbose logging is on.
    """
    return smarter_settings.verbose_logging


verbose_logger = WaffleSwitchedLoggerWrapper(logger, should_log_verbose)  # type: ignore[assignment]


class TimestampedModel(models.Model, SmarterHelperMixin):
    """
    Abstract base model for all Django models in Smarter, with automatic timestamp fields and utility methods.

    This class should be used as the base class for all models in the project to ensure
    consistent tracking of creation and modification times. It adds ``created_at`` and
    ``updated_at`` fields, and provides validation and time-difference utilities.

    **Example Usage:**

    .. code-block:: python

        from smarter.lib.django.models import TimestampedModel

        class MyModel(TimestampedModel):
            name = models.CharField(max_length=100)

        # Creating an instance
        obj = MyModel.objects.create(name="Example")
        print(obj.created_at)  # Timestamp of creation
        print(obj.updated_at)  # Timestamp of last update

        # Checking elapsed time since last update
        seconds = obj.elapsed_updated
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
        - The hashed ID methods provide a way to encode and decode object IDs for use in URLs
          in cases where you want to avoid exposing raw database IDs.
    """

    HASH_PREFIX = "r"
    HASH_SUFFIX = "x"
    HASH_FLOOR = 1000000
    _hash_regex = None
    #: Seconds that ``get_cached_object()`` caches a row, from ``smarter_settings.cache_expiration``.
    cache_expiration: ClassVar[int] = smarter_settings.cache_expiration
    #: The row's primary key, which Django adds to every concrete model. Declared, without a value,
    #: only so that type checkers know it: Django ignores a bare annotation.
    id: int

    # pylint: disable=missing-class-docstring
    class Meta:
        abstract = True

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

    ###########################################################################
    # public methods for internal use.
    ###########################################################################

    @classmethod
    def hash_regex(cls) -> re.Pattern:
        """
        Returns a regex pattern that matches the hashed ID format for this model anywhere in a string.

        The hashed ID format is defined by the ``HASH_PREFIX`` and ``HASH_SUFFIX`` class attributes,
        with a base64-encoded string in between. This regex can be used to validate or extract
        hashed IDs from strings, including when embedded in URLs.

        :returns: A regex pattern for matching hashed IDs.
        """
        if cls._hash_regex is None:
            cls._hash_regex = re.compile(f"{cls.HASH_PREFIX}[A-Za-z0-9_-]+{cls.HASH_SUFFIX}")
        return cls._hash_regex

    @property
    def is_billable_resource(self) -> bool:
        """
        Indicates whether the model instance is considered a billable resource.

        This property can be overridden in subclasses to specify which models are billable.
        By default, it returns False, indicating that the base TimestampedModel is not billable.

        :returns: True if the instance is billable, False otherwise.
        """
        return False

    @cached_property
    def ready(self) -> bool:
        """
        Check if the model instance is ready for use.

        :returns: True if the instance is ready, False otherwise.
        """
        return self.pk is not None

    @cached_property
    def hashed_id(self) -> str:
        """
        Returns a URL-friendly hashed version of the object's ID for use in URLs and other contexts where an obscured, non-identifying, non-sequential identifier is preferred.

        Encoding scheme:

        1. Take the object's ID and add a large constant (HASH_FLOOR) to ensure it's not easily guessable.
        2. Convert the resulting number to a string and encode it using URL-safe base64 encoding.
        3. Remove any padding characters from the encoded string.
        4. Add a prefix and suffix to the encoded string to create a recognizable format.

        Example:

        .. code-block:: python

            obj = MyModel.objects.create()
            print(obj.id)  # e.g., 123
            print(obj.hashed_id)  # e.g., "rc2x"

        :returns: Hashed ID string (URL-safe, no padding).
        """
        id_value = int(self.id) + self.HASH_FLOOR  # type: ignore[union-attr]
        id_bytes = str(id_value).encode()
        encoded_bytes = base64.urlsafe_b64encode(id_bytes)
        encoded_text = encoded_bytes.decode()
        encoded = encoded_text.rstrip("=")
        padded_encoded = f"{self.HASH_PREFIX}{encoded}{self.HASH_SUFFIX}"
        return padded_encoded

    @classmethod
    def id_from_hashed_id(cls, hashed_id: str) -> Optional[int]:
        """
        Decodes a hashed ID back to the original object ID.

        Decoding scheme:

        1. Validate that the hashed ID starts with the expected prefix and ends with the expected suffix.
        2. Remove the prefix and suffix to isolate the base64-encoded string.
        3. Add padding if necessary to make the length of the encoded string a multiple of 4.
        4. Decode the base64 string to get the original number as a string.
        5. Convert the decoded string to an integer and subtract the HASH_FLOOR to get the original ID.

        Example:

        .. code-block:: python

            my_record = MyModel.objects.create()
            print(my_record.id)  # e.g., 123
            hashed_id = my_record.hashed_id  # e.g., "rc2x"

            original_id = MyModel.id_from_hashed_id(hashed_id)
            print(original_id)  # Should print the original ID (e.g., 123)

        :param hashed_id: The hashed ID string to decode (URL-safe, no padding).
        :returns: The original object ID if decoding is successful, otherwise None.
        """
        logger_prefix = f"{logging.SmarterFormattedText.text(cls.__name__)}.id_from_hashed_id()"
        try:
            if not hashed_id.startswith(cls.HASH_PREFIX) or not hashed_id.endswith(cls.HASH_SUFFIX):
                logger.warning(
                    "%s Hashed ID '%s' does not start with '%s' or end with '%s'.",
                    logger_prefix,
                    hashed_id,
                    cls.HASH_PREFIX,
                    cls.HASH_SUFFIX,
                )
                return None
            encoded_str = hashed_id[len(cls.HASH_PREFIX) : -len(cls.HASH_SUFFIX)]
            # Add padding if needed
            padding = "=" * (-len(encoded_str) % 4)
            encoded_str += padding
            decoded_bytes = base64.urlsafe_b64decode(encoded_str.encode())
            decoded_str = decoded_bytes.decode()
            retval = int(decoded_str) - cls.HASH_FLOOR
            verbose_logger.debug(
                "%s decoded %s.hashed_id: %s to id: %d",
                logger_prefix,
                cls.__name__,
                hashed_id,
                retval,
            )
            return retval
        except (base64.binascii.Error, ValueError) as e:  # type: ignore[name-defined]
            logger.error(
                "%s Failed to decode %s.hashed_id '%s': %s",
                logger_prefix,
                cls.__name__,
                hashed_id,
                e,
            )
            return None
        # pylint: disable=broad-except
        except Exception as e:
            logger.exception(
                "%s Unexpected error while decoding %s.hashed_id '%s': %s",
                logger_prefix,
                cls.__name__,
                hashed_id,
                e,
            )
            return None

    @classmethod
    def find_hash(cls, value: str) -> Optional[str]:
        """
        Finds and returns the first substring in the given value that matches the hashed ID format.

        :param value: The string to search for a hashed ID.
        :returns: The first matching hashed ID if found, otherwise None.
        """
        logger_prefix = f"{logging.SmarterFormattedText.text(cls.__name__)}.find_hash()"
        verbose_logger.debug(
            "%s - Searching for hashed ID in value: %s",
            logger_prefix,
            value,
        )
        pattern = cls.hash_regex()
        match = pattern.search(value)
        retval = match.group(0) if match else None
        if retval:
            verbose_logger.debug(
                "%s - Found hashed ID: %s",
                logger_prefix,
                retval,
            )
        else:
            verbose_logger.debug(
                "%s - No hashed ID found in value: %s",
                logger_prefix,
                value,
            )
        return retval

    ###########################################################################
    # public methods for public use.
    ###########################################################################

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

        **Example**

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

        :param args: Positional arguments, forwarded to Django's ``save()``.
        :param kwargs: Keyword arguments, forwarded to Django's ``save()``.
        :raises SmarterValueError: if :meth:`validate` raises any exception. Its message names the
            model and the row's primary key, never the field values: a row can hold secrets, and
            the message reaches logs and api error responses.
        """
        model_name = self.__class__.__name__
        try:
            self.validate()
        except (ValidationError, SmarterValueError) as e:
            raise SmarterValueError(
                f"TimestampedModel().save() validation error: {e} | model={model_name} pk={self.pk}"
            ) from e
        except Exception as e:
            raise SmarterValueError(
                f"TimestampedModel().save() unexpected error during validation: {e} | model={model_name} pk={self.pk}"
            ) from e
        super().save(*args, **kwargs)

    @cached_property
    def record_locator(self) -> str:
        """
        Returns a short, URL-friendly record locator derived from the object's ID.

        Example:

        .. code-block:: python

            obj = MyModel.objects.create(name="Example")
            print(obj.id)  # e.g., 123
            print(obj.record_locator)  # e.g., "llmclient-rc2x"

        :returns: Record locator string (URL-safe, no padding).
        """
        prefix = str(self.__class__.__name__).lower()
        return f"{prefix}-{self.hashed_id}"

    @classmethod
    def get_object_by_locator(cls, locator: str) -> Optional["TimestampedModel"]:
        """
        Retrieves an object based on its record locator.

        Example:

        .. code-block:: python

            obj = MyModel.objects.create()
            print(obj.id)  # e.g., 123
            locator = obj.record_locator # e.g., "mymodel-rc2x"

            retrieved_obj = MyModel.get_object_by_locator(locator)
            print(type(retrieved_obj))  # Should be <class 'MyModel'>
            print(retrieved_obj)  # Should be the same as obj

        :param locator: The record locator string to decode and search for.
        :returns: The model instance if found, otherwise None. A failure to decode or find the
            object is logged, and returns None.
        """
        logger_prefix = f"{logging.SmarterFormattedText.text(cls.__name__)}.get_object_by_locator()"
        verbose_logger.debug(
            "%s Attempting to retrieve object with locator: %s",
            logger_prefix,
            locator,
        )
        try:
            prefix = str(cls.__name__).lower()
            if not locator.startswith(f"{prefix}-"):
                logger.warning(
                    "%s Locator '%s' does not start with expected prefix '%s-'.",
                    logger_prefix,
                    locator,
                    prefix,
                )
                return None
            hashed_part = locator[len(prefix) + 1 :].lstrip("0")
            id_value = cls.id_from_hashed_id(hashed_part)
            if id_value is None:
                logger.warning(
                    "%s Failed to decode hashed part '%s' from locator '%s'.",
                    logger_prefix,
                    hashed_part,
                    locator,
                )
                return None
            obj = cls.get_cached_object(pk=id_value)
            if obj is None:
                logger.warning(
                    "%s No object found with ID %d decoded from locator '%s'.",
                    logger_prefix,
                    id_value,
                    locator,
                )
            else:
                verbose_logger.debug(
                    "%s Successfully retrieved object with ID %d from locator '%s'.",
                    logger_prefix,
                    id_value,
                    locator,
                )
            return obj  # type: ignore[return-value]
        # pylint: disable=broad-except
        except Exception as e:
            logger.exception(
                "%s Unexpected error while retrieving object with locator '%s': %s",
                logger_prefix,
                locator,
                e,
            )
            return None

    @property
    def elapsed_updated(self, dt=None) -> Optional[int]:
        """
        The number of whole seconds since the model's ``updated_at`` timestamp.

        It is a property, so it always compares ``updated_at`` with the current time: the ``dt``
        parameter can't be passed, and is always None. A naive ``updated_at`` is compared with
        the naive current time, and an aware one with the current UTC time.

        **Example**

        .. code-block:: python

            obj = MyModel.objects.get(pk=1)
            seconds = obj.elapsed_updated
            print(f"Seconds since last update: {seconds}")

        :returns: The absolute difference in seconds between ``updated_at`` and now, or None if
            ``updated_at`` is not set, e.g. because the object has not been saved.
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

    def to_json(self) -> SmarterDictType:
        """
        Serialize the model instance to a JSON-compatible dictionary.

        This method uses the custom ``SmarterJSONEncoder`` to ensure that all fields,
        including timestamps and any complex data types, are properly serialized.

        :returns: A dictionary representation of the model instance suitable for JSON serialization.
        :raises SmarterValueError: if the instance can't be serialized.
        """
        try:
            data = model_to_dict(self)
            data["record_locator"] = self.record_locator
            data["elapsed_updated"] = self.elapsed_updated
            return to_jsonable(data)
        except Exception as e:
            logger.exception(
                "%s.to_json() - Error serializing model to JSON. model=%s, pk=%s, exception: %s",
                self.formatted_class_name,
                self.__class__.__name__,
                self.pk,
                e,
            )
            raise SmarterValueError(f"Error serializing model to JSON: {e}") from e

    @classmethod
    def get_cached_object(
        cls, invalidate: Optional[bool] = False, pk: Optional[int] = None, **kwargs
    ) -> Optional[models.Model]:
        """
        Retrieve a model instance by primary key, using caching to optimize performance.

        This method is selectively overridden in models that inherit from TimestampedModel to provide class-specific
        function parameters.

        **Example**

        .. code-block:: python

            # Retrieve by primary key
            instance = MyModel.get_cached_object(pk=1)

        :param invalidate: Whether to drop the cached row, and read it again from the database.
        :param pk: The primary key of the model instance to retrieve.
        :param kwargs: Ignored here; subclasses that override this method use them.
        :returns: The model instance.
        :raises NotImplementedError: if called on an abstract model class.
        :raises ~django.core.exceptions.ObjectDoesNotExist: the model's ``DoesNotExist``, if ``pk``
            is missing or no row has it.
        """
        logger_prefix = SmarterFormattedText.text(__name__ + "." + TimestampedModel.__name__)

        if cls._meta.abstract:
            raise NotImplementedError(
                "get_cached_object() must be called on a concrete model class, not an abstract base class."
            )

        @cache_results(timeout=cls.cache_expiration)
        def _get_model_by_pk(pk: int, class_name: str = cls.__name__) -> Optional[models.Model]:

            try:
                verbose_logger.debug(
                    "%s._get_model_by_pk() %s called with pk: %s, invalidate=%s",
                    logger_prefix,
                    class_name,
                    pk,
                    invalidate,
                )
                retval = cls.objects.get(pk=pk)
                verbose_logger.debug(
                    "%s._get_model_by_pk() fetched and cached %s pk: %s",
                    logger_prefix,
                    class_name,
                    pk,
                )
                return retval
            except cls.DoesNotExist as e:
                verbose_logger.debug(
                    "%s._get_model_by_pk() no object found for %s pk: %s",
                    logger_prefix,
                    class_name,
                    pk,
                )
                raise cls.DoesNotExist(f"{class_name} object with pk '{pk}' does not exist.") from e

        if invalidate:
            _get_model_by_pk.invalidate(pk, cls.__name__)

        if not pk:
            verbose_logger.debug("%s.get_cached_object() called with no pk", logger_prefix)
            raise cls.DoesNotExist(f"Must provide a 'pk' to retrieve a {cls.__name__} object.")

        # same args as invalidate() above, so that both produce the same cache key
        return _get_model_by_pk(pk, cls.__name__)

    @classmethod
    def get_cached_objects(cls, invalidate: Optional[bool] = False, **kwargs) -> QuerySet["TimestampedModel"]:
        """
        Return every row of the model.

        Subclasses override it with filters, e.g. a user profile, and cache those results. The
        unfiltered list is not cached: a queryset is lazy, so returning it costs nothing, while
        caching it would store the whole table in Redis, and refill it after every save.

        **Example**

        .. code-block:: python

            # Retrieve all instances
            instances = MyModel.get_cached_objects()

        :param invalidate: Accepted for the subclasses' signature. Nothing is cached here.
        :param kwargs: Ignored here; subclasses that override this method use them.
        :returns: A queryset of all model instances.
        :raises NotImplementedError: if called on an abstract model class.
        """
        if cls._meta.abstract:
            raise NotImplementedError(
                "get_cached_objects() must be called on a concrete model class, not an abstract base class."
            )

        queryset = cls.objects.all()
        return queryset

    def __str__(self) -> str:
        """
        Return the model's class name and id, e.g. ``LLMClient(id=1)``.

        :returns: The short description of the row.
        """
        return f"{self.__class__.__name__}(id={getattr(self, 'id', None)})"

    def __repr__(self) -> str:
        """
        Return the model's class name, id and timestamps, for debugging.

        :returns: The description of the row.
        """
        return f"<{self.__class__.__name__} id={getattr(self, 'id', None)} created_at={self.created_at} updated_at={self.updated_at}>"


__all__ = ["TimestampedModel"]
