"""This module contains the Django models for SAM."""

import hashlib
import uuid

from django.db import models

from smarter.lib.django.model_helpers import TimestampedModel
from smarter.lib.django.user import User

from .enum import SmarterJournalCliCommands, SmarterJournalThings


class SAMJournal(TimestampedModel):
    """Maintains a journal of all the changes made to the SAM database via api/v1/cli manifests."""

    key = models.CharField(default=None, editable=False, max_length=64, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    thing = models.CharField(max_length=64, choices=SmarterJournalThings.choices())
    command = models.CharField(max_length=64, choices=SmarterJournalCliCommands.choices())
    request = models.JSONField()
    response = models.JSONField()

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()
        super().save(*args, **kwargs)
