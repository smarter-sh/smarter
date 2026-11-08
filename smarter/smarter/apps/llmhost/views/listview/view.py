"""
The LLM Host and LLM Host Compute list pages, which the single-page console serves (ADR-035).

The pages are ``/llmhost/`` and ``/llmhost/compute/``.

The console renders each package's list at its page's path, and the lists call their list apis,
:mod:`smarter.apps.llmhost.views.listview.api`. The pages keep their view classes, named after the list apis', which
:func:`smarter.lib.django.listview.listview_registry` pairs them with, so that the dashboard's global search links to
them.
"""

from smarter.apps.dashboard.views.console_app import ConsoleAppView


class LLMHostListView(ConsoleAppView):
    """The LLM Host list page: the single-page console's, at the path that Django served it at."""


class LLMHostComputeListView(ConsoleAppView):
    """The LLM Host Compute list page: the single-page console's, at the path that Django served it at."""
