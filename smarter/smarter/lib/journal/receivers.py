# pylint: disable=unused-argument
"""
Django signal receivers for the Smarter Journal.

They only log. A journal entry's request and response documents hold credentials and user content,
so the receivers log an entry's key, thing, command and status code, never its documents.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from smarter.common.helpers.console_helpers import formatted_text
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
module_prefix = __name__


@receiver(post_save, sender=SAMJournal)
def samjournal_post_save(sender, instance: SAMJournal, created, **kwargs):
    """Signal receiver for created/saved of SAMJournal model."""
    logger.debug(
        "%s SAMJournal: %s, thing: %s, command: %s, status_code: %s, created: %s",
        f"{formatted_text(module_prefix)}.samjournal_post_save()",
        instance.key,
        instance.thing,
        instance.command,
        instance.status_code,
        created,
    )


@receiver(post_delete, sender=SAMJournal)
def samjournal_post_delete(sender, instance: SAMJournal, **kwargs):
    """Signal receiver for deleted of SAMJournal model."""
    logger.debug(
        "%s SAMJournal: %s",
        f"{formatted_text(module_prefix)}.samjournal_post_delete()",
        instance.key,
    )


@receiver(journal_entry_created)
def journal_entry_created_receiver(sender, journal: SAMJournal, **kwargs):
    """Signal receiver for journal_entry_created signal."""
    logger.debug(
        "%s sender: %s, journal: %s, thing: %s, command: %s, status_code: %s",
        f"{formatted_text(module_prefix)}.journal_entry_created()",
        sender,
        journal.key,
        journal.thing,
        journal.command,
        journal.status_code,
    )


@receiver(journal_entry_failed)
def journal_entry_failed_receiver(sender, user, thing, command, status, request, response, error, **kwargs):
    """
    Signal receiver for journal_entry_failed signal.

    It logs at error level, whatever the waffle switches, because a missing journal entry is a gap in an
    audit record. Operators monitor the logs for ``could not create journal entry``.
    """
    prefix = f"{formatted_text(module_prefix)}.journal_entry_failed()"
    error_logger.error(
        "%s sender=%s, user=%s, thing=%s, command=%s, status=%s\nrequest=%s\nresponse: %s",
        prefix,
        sender,
        user,
        thing,
        command,
        status,
        request,
        response,
    )
    error_logger.error("%s could not create journal entry: %s", prefix, error)


@receiver(journal_entry_accessed)
def journal_entry_accessed_receiver(sender, journal: SAMJournal, user, **kwargs):
    """Signal receiver for journal_entry_accessed signal."""
    logger.debug(
        "%s sender: %s, journal: %s, user: %s",
        f"{formatted_text(module_prefix)}.journal_entry_accessed()",
        sender,
        journal.key,
        user,
    )


@receiver(journal_entries_listed)
def journal_entries_listed_receiver(sender, user, count, **kwargs):
    """Signal receiver for journal_entries_listed signal."""
    logger.debug(
        "%s sender: %s, user: %s, count: %s",
        f"{formatted_text(module_prefix)}.journal_entries_listed()",
        sender,
        user,
        count,
    )
