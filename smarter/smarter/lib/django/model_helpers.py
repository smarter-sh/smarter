"""Common model utils."""

from django.db import models


class TimestampedModel(models.Model):
    """Timestamped model to use as a baseclass for all models in this project."""

    created_at = models.DateTimeField(auto_now_add=True, null=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, null=True, editable=False)

    # pylint: disable=missing-class-docstring
    class Meta:
        abstract = True

    def validate(self):
        """Validate the model."""
        self.full_clean()
