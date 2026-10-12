"""
URL configuration for the Smarter Journal api.

These are mounted at ``/api/v1/journal/``. See :mod:`smarter.lib.journal.api.v1.views`.
"""

from django.urls import path

from smarter.common.utils import to_snake_case
from smarter.lib.journal.const import namespace

from .views import SAMJournalListView, SAMJournalView

app_name = namespace


class SAMJournalApiV1ReverseViews:
    """
    Reverse view names for the Smarter Journal api.

    Example
    -------
    .. code-block:: python

        from django.urls import reverse
        url = reverse(
            f"{SAMJournalApiV1ReverseViews.namespace}:{SAMJournalApiV1ReverseViews.journal_view}",
            kwargs={"key": journal.key},
        )
    """

    namespace = "api:v1:journal"

    list_view = to_snake_case(SAMJournalListView.__name__)
    journal_view = to_snake_case(SAMJournalView.__name__)


urlpatterns = [
    path("", SAMJournalListView.as_view(), name=SAMJournalApiV1ReverseViews.list_view),
    path("<str:key>/", SAMJournalView.as_view(), name=SAMJournalApiV1ReverseViews.journal_view),
]
