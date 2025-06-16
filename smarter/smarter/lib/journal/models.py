"""This module contains the Django models for SAM."""

from django.db import models

from smarter.common.utils import hash_factory
from smarter.lib.django.user import User

from .enum import SmarterJournalCliCommands, SmarterJournalThings


class SAMJournal(models.Model):
    """Maintains a journal of all the changes made to the SAM database via api/v1/cli manifests."""

    key = models.CharField(primary_key=True, default=None, editable=False, max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    thing = models.CharField(
        max_length=24, choices=SmarterJournalThings.choices(), default=SmarterJournalThings.CHAT.value, blank=True
    )
    command = models.CharField(
        max_length=24,
        choices=SmarterJournalCliCommands.choices(),
        blank=True,
        default=SmarterJournalCliCommands.CHAT.value,
    )
    request = models.JSONField()
    response = models.JSONField()
    status_code = models.PositiveSmallIntegerField(default=200)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = hash_factory(length=64)
        super().save(*args, **kwargs)
