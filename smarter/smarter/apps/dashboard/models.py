# -*- coding: utf-8 -*-
"""Account models."""

from django.db import models

# our stuff
from smarter.apps.common.model_utils import TimestampedModel


class EmailContactList(TimestampedModel):
    """Model to persist emails collected from landing page."""

    email = models.EmailField(unique=True, blank=False, null=False)

    class Meta:
        """Metadata for the model."""

        verbose_name = "Email Contact"
        verbose_name_plural = "Email Contacts"
