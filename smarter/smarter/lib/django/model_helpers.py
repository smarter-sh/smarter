"""Common model utils."""

import datetime
from logging import getLogger

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.timezone import is_aware, make_aware


logger = getLogger(__name__)


class TimestampedModel(models.Model):
    """Timestamped model to use as a baseclass for all models in this project."""

    created_at = models.DateTimeField(auto_now_add=True, null=True, editable=False, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, editable=False, db_index=True)

    # pylint: disable=missing-class-docstring
    class Meta:
        abstract = True

    def validate(self):
        """Validate the model."""
        # this breaks on SmarterAuthToken.objects.create()
        # self.full_clean()
        logger.warning("TimestampedModel().validate() called but not applied on %s", self.__class__.__name__)

    def save(self, *args, **kwargs):
        """Override save to validate before saving."""
        try:
            self.validate()
        except ValidationError as e:
            raise ValidationError(
                f"TimestampedModel().save() validation error: {e} | args={args} kwargs={kwargs} | model={self.__class__.__name__} | field_values={self.__dict__}"
            ) from e
        super().save(*args, **kwargs)

    @property
    def elapsed_updated(self, dt=None) -> int:
        """
        Returns the absolute time difference in seconds between the given datetime `dt`
        and this object's `updated_at` field.
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
