# pylint: disable=unused-argument
"""
Django signal receivers for the Smarter Journal.

They only log. A journal entry's request and response documents hold user content, e.g. prompts,
manifests and LLM responses, so the receivers log an entry's key, thing, command and status code, never its documents.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import SAMJournal
from .signals import (
    journal_entries_listed,
    journal_entry_accessed,
    journal_entry_created,
    journal_entry_failed,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.RECEIVER_LOGGING])
error_logger = logging.getSmarterLogger(__name__)
"""Logs whatever the waffle switches, for a journal entry that could not be saved."""


@receiver(post_save, sender=SAMJournal)
def samjournal_post_save(sender, instance: SAMJournal, created, **kwargs):
    """
    Signal receiver for created/saved of SAMJournal model: log the entry at DEBUG.

    :param sender: The SAMJournal model.
    :param instance: The saved entry.
    :param created: True if the entry was created.
    :param kwargs: The rest of the signal's arguments.
    """
    logger.debug(
        "SAMJournal: %s, thing: %s, command: %s, status_code: %s, created: %s",
        instance.key,
        instance.thing,
        instance.command,
        instance.status_code,
        created,
    )


@receiver(post_delete, sender=SAMJournal)
def samjournal_post_delete(sender, instance: SAMJournal, **kwargs):
    """
    Signal receiver for deleted of SAMJournal model: log the entry's key at DEBUG.

    :param sender: The SAMJournal model.
    :param instance: The deleted entry.
    :param kwargs: The rest of the signal's arguments.
    """
    logger.debug(
        "SAMJournal: %s",
        instance.key,
    )


@receiver(journal_entry_created)
def journal_entry_created_receiver(sender, journal: SAMJournal, **kwargs):
    """
    Signal receiver for journal_entry_created signal: log the entry at DEBUG.

    :param sender: The class that sent the signal.
    :param journal: The new entry.
    :param kwargs: The rest of the signal's arguments.
    """
    logger.debug(
        "sender: %s, journal: %s, thing: %s, command: %s, status_code: %s",
        sender,
        journal.key,
        journal.thing,
        journal.command,
        journal.status_code,
    )


# the arguments that journal_entry_failed sends.
# pylint: disable=too-many-arguments,too-many-positional-arguments
@receiver(journal_entry_failed)
def journal_entry_failed_receiver(sender, user, thing, command, status, request, response, error, **kwargs):
    """
    Signal receiver for journal_entry_failed signal.

    It logs at error level, whatever the waffle switches, because a missing journal entry is a gap in an
    audit record. Operators monitor the logs for ``could not create journal entry``. The request and
    response documents are not logged, because they hold user content.

    :param sender: The class that sent the signal.
    :param user: The user the entry was for, or None.
    :param thing: The kind of resource.
    :param command: The command that was journaled.
    :param status: The response's http status code.
    :param request: The serialized request. Not logged.
    :param response: The response document. Not logged.
    :param error: The exception that stopped the entry from being created.
    :param kwargs: Any other signal arguments.
    """
    error_logger.error(
        "sender=%s, user=%s, thing=%s, command=%s, status=%s",
        sender,
        user,
        thing,
        command,
        status,
    )
    error_logger.error(
        "could not create journal entry: %s",
        error,
    )


@receiver(journal_entry_accessed)
def journal_entry_accessed_receiver(sender, journal: SAMJournal, user, **kwargs):
    """
    Signal receiver for journal_entry_accessed signal: log the access at DEBUG.

    :param sender: The class that sent the signal.
    :param journal: The entry that was read.
    :param user: The user who read it.
    :param kwargs: The rest of the signal's arguments.
    """
    logger.debug(
        "sender: %s, journal: %s, user: %s",
        sender,
        journal.key,
        user,
    )


@receiver(journal_entries_listed)
def journal_entries_listed_receiver(sender, user, count, **kwargs):
    """
    Signal receiver for journal_entries_listed signal: log the listing at DEBUG.

    :param sender: The class that sent the signal.
    :param user: The user who listed the entries.
    :param count: The number of entries listed.
    :param kwargs: The rest of the signal's arguments.
    """
    logger.debug(
        "sender: %s, user: %s, count: %s",
        sender,
        user,
        count,
    )
