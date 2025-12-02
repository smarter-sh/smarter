"""This module contains the Django models for SAM."""

from django.conf import settings
from django.db import models

from smarter.common.utils import hash_factory

from .enum import SmarterJournalCliCommands, SmarterJournalThings


class SAMJournal(models.Model):
    """
    Model representing a journal entry for changes made to the SAM database.

    This model is used to maintain a comprehensive log of all modifications performed on the SAM database,
    whether those changes are initiated via the API (``api/v1``) or through CLI manifests. Each journal entry
    records the details of the operation, including the user responsible, the type of entity affected, the
    command executed, the request and response payloads, and the resulting status code.

    Examples
    --------
    Creating a new journal entry::

        entry = SAMJournal(
            user=request.user,
            thing=SmarterJournalThings.CHAT.value,
            command=SmarterJournalCliCommands.CREATE.value,
            request={"data": "example"},
            response={"result": "success"},
            status_code=201
        )
        entry.save()

    See Also
    --------
    smarter.common.utils.hash_factory
        Utility function used to generate unique keys for journal entries.
    smarter.lib.journal.enum.SmarterJournalCliCommands
        Enumeration of valid CLI commands for journal entries.
    smarter.lib.journal.enum.SmarterJournalThings
        Enumeration of valid entity types for journal entries.
    """

    key = models.CharField(primary_key=True, default=None, editable=False, max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True, db_index=True)
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
