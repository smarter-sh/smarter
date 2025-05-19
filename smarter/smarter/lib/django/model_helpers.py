"""Common model utils."""

from django.core.exceptions import ValidationError
from django.db import models


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
        self.full_clean()

    def save(self, *args, **kwargs):
        """Override save to validate before saving."""
        try:
            self.validate()
        except ValidationError as e:
            raise ValidationError(
                f"TimestampedModel().save() validation error: {e} | args={args} kwargs={kwargs} | model={self.__class__.__name__} | field_values={self.__dict__}"
            ) from e
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.__class__.__name__}(id={getattr(self, 'id', None)})"
