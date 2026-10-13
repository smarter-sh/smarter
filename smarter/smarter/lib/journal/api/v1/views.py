"""
Smarter Journal api views.

They are mounted at ``/api/v1/journal/``, and only superusers may call them: a journal entry's
request document holds the caller's headers and cookies, including its api key. Each read is
signaled, with :data:`smarter.lib.journal.signals.journal_entry_accessed` or
:data:`smarter.lib.journal.signals.journal_entries_listed`.
"""

from django.db.models import QuerySet
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.lib import logging
from smarter.lib.django.pagination import paginate_listview
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAdminAPIView,
    SmarterAdminListAPIView,
)
from smarter.lib.journal.contract.models import (
    SAMJournalApiEntry,
    SAMJournalApiEntrySummary,
    SAMJournalApiPage,
)
from smarter.lib.journal.models import SAMJournal
from smarter.lib.journal.serializers import (
    SAMJournalMiniSerializer,
    SAMJournalSerializer,
)
from smarter.lib.journal.signals import journal_entries_listed, journal_entry_accessed

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.API_LOGGING])

SEARCH_FIELDS = ("key", "thing", "command")
"""The fields that a search of the list matches."""

SORT_FIELDS = {
    "createdAt": "created_at",
    "user": "user__username",
    "thing": "thing",
    "command": "command",
    "statusCode": "status_code",
}
"""The columns that the list may be sorted by.

See :data:`smarter.lib.django.pagination.DEFAULT_SORT_FIELDS`.
"""


def journal_entries() -> QuerySet[SAMJournal]:
    """Every journal entry, newest first, with its user."""
    return SAMJournal.objects.select_related("user").order_by("-created_at")


class SAMJournalView(SmarterAdminAPIView):
    """A journal entry, by its key, with its request and response documents: a :class:`SAMJournalApiEntry`."""

    serializer_class = SAMJournalSerializer

    def get_queryset(self) -> QuerySet[SAMJournal]:
        return journal_entries()

    def get(self, request: Request, key: str, *args, **kwargs):
        """Return the journal entry."""
        journal = get_object_or_404(self.get_queryset(), key=key)
        journal_entry_accessed.send(sender=self.__class__, journal=journal, user=request.user)
        return Response(SAMJournalApiEntry.from_model(journal).model_dump(mode="json"))

    def post(self, request: Request, key: str, *args, **kwargs):
        """Same as get().

        Smarter detail views are also served by POST.
        """
        return self.get(request, key, *args, **kwargs)


class SAMJournalListView(SmarterAdminListAPIView):
    """
    One page of the journal entries, newest first, without their request and response documents: a.

    :class:`SAMJournalApiPage`.

    The query parameters ``page``, ``page_size``, ``search`` and ``ordering`` are those of
    :func:`smarter.lib.django.pagination.paginate_listview`. A search matches an entry's key, thing or
    command.
    """

    serializer_class = SAMJournalMiniSerializer

    def get_queryset(self) -> QuerySet[SAMJournal]:
        return journal_entries()

    def list(self, request: Request, *args, **kwargs):
        """Return one page of the journal entries, and a description of the page."""
        page, pagination = paginate_listview(
            request, self.get_queryset(), search_fields=SEARCH_FIELDS, sort_fields=SORT_FIELDS
        )
        journal_entries_listed.send(sender=self.__class__, user=request.user, count=pagination["count"])
        logger.debug("%s.list() - user: %s, pagination: %s", self.formatted_class_name, request.user, pagination)
        response = SAMJournalApiPage(
            objects=[SAMJournalApiEntrySummary.from_model(journal) for journal in page],
            pagination=pagination,  # type: ignore[arg-type]
        )
        return JsonResponse(response.model_dump(mode="json"))

    def post(self, request: Request, *args, **kwargs):
        """Same as get().

        Smarter list views are also served by POST.
        """
        return self.list(request, *args, **kwargs)
