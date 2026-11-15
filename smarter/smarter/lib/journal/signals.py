"""Signals for the Smarter Journal."""

from django.dispatch import Signal

journal_entry_created = Signal()
"""
Signal sent when a journal entry is saved, by the Celery worker that saves it, or by the response.

itself when the entry could not be queued.

**Arguments:**

- ``journal`` (:class:`~smarter.lib.journal.models.SAMJournal`): The new journal entry.

Example::

    journal_entry_created.send(sender=SAMJournal, journal=journal)
"""

journal_entry_failed = Signal()
"""
Signal sent when a journal entry could not be saved.

It is sent by the journaled response when the entry could neither be queued nor saved, and the
response is returned without a key, or by the Celery task, when its last try fails.

**Arguments:**

- ``user`` (``User`` or ``int``): The user who made the request, the user's id from the task, or None.
- ``thing`` (``str``): The journal's thing, e.g. Guardrail.
- ``command`` (``str``): The journal's command, e.g. apply.
- ``status`` (``int``): The response's http status.
- ``request`` (``HttpRequest``): The request, or None from the task.
- ``response`` (``dict``): The response's JSON, or None if it could not be serialized, or from the task.
- ``error`` (``Exception``): The error that prevented the entry from being saved.

Example::

    journal_entry_failed.send(
        sender=self.__class__,
        user=user,
        thing=thing,
        command=command,
        status=status,
        request=request,
        response=response,
        error=e,
    )
"""

journal_entry_accessed = Signal()
"""
Signal sent when a journal entry is read through the journal api.

Journal entries hold credentials and user content, so every read is signaled.

**Arguments:**

- ``journal`` (:class:`~smarter.lib.journal.models.SAMJournal`): The journal entry that was read.
- ``user`` (``User``): The user who read it.

Example::

    journal_entry_accessed.send(sender=self.__class__, journal=journal, user=request.user)
"""

journal_entries_listed = Signal()
"""
Signal sent when journal entries are listed through the journal api.

**Arguments:**

- ``user`` (``User``): The user who listed them.
- ``count`` (``int``): The number of entries that match the request's search.

Example::

    journal_entries_listed.send(sender=self.__class__, user=request.user, count=count)
"""
