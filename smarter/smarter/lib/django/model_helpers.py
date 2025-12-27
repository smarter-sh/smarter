"""Django ORM base model"""

import datetime
from logging import getLogger
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.timezone import is_aware, make_aware
from taggit.managers import TaggableManager

from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.validators import SmarterValidator


logger = getLogger(__name__)


def validate_no_spaces(value) -> None:
    """Validate that the string does not contain spaces."""
    if " " in value:
        raise SmarterValueError(f"Value must not contain spaces: {value}")


class TimestampedModel(models.Model):
    """
    Abstract base model for all Django ORM models in the Smarter project, providing automatic
    timestamp fields and utility methods.

    This class should be used as the base class for all models in the project to ensure
    consistent tracking of creation and modification times. It adds ``created_at`` and
    ``updated_at`` fields, and provides validation and time-difference utilities.

    **Example Usage:**

    .. code-block:: python

        from smarter.smarter.lib.django.model_helpers import TimestampedModel

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

    """

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
        super().save(*args, **kwargs)

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

    def __str__(self):
        return f"{self.__class__.__name__}(id={getattr(self, 'id', None)})"


class MetaDataModel(TimestampedModel):
    """
    Abstract base model that adds SAM metadata fields to a
    TimestampedModel Django ORM model. These are the
    the common fields that makeup the Pydantic SAM metadata model,
    along with timestamp fields for create/modify tracking.

    **Example Usage:**

    .. code-block:: python

        from smarter.smarter.lib.django.model_helpers import MetaDataModel
        from smarter.apps.account.models import User

        class MyModel(MetaDataModel):
            name = models.CharField(max_length=100)

    """

    # pylint: disable=missing-class-docstring
    class Meta:
        abstract = True

    name = models.CharField(
        blank=True,
        default="",
        max_length=255,
        help_text="Name in camelCase, e.g., 'apiKey', no special characters.",
        validators=[SmarterValidator.validate_snake_case, validate_no_spaces],
    )
    description = models.TextField(
        help_text="A brief description of this resource. Be verbose, but not too verbose.",
        blank=True,
        default="",
    )
    version = models.CharField(max_length=255, default="1.0.0")
    tags = TaggableManager(
        blank=True,
        help_text="Tags for categorizing and organizing this resource.",
    )
    annotations = models.JSONField(default=list, blank=True, help_text="Key-value pairs for annotating this resource.")

    def validate(self):
        """
        Validate the model.
        """
        super().validate()
        # version should be a semantic version: MAJOR.MINOR.PATCH
        if self.version and not SmarterValidator.is_valid_semantic_version(self.version):
            raise SmarterValueError(f"Version '{self.version}' is not a valid semantic version (MAJOR.MINOR.PATCH).")

    def __str__(self):
        return f"{self.__class__.__name__}(id={getattr(self, 'id', None)})"
