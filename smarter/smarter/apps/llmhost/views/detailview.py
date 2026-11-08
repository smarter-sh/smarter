"""
The manifest pages of an LLMHost and of an LLMHostCompute, which the single-page console serves (ADR-035).

The pages are ``/llmhost/llmhosts/<hashed id>/`` and ``/llmhost/compute/<hashed id>/``. The console shows the
resource's manifest in the manifest editor, from the dashboard's resource api,
:mod:`smarter.apps.dashboard.resource_detail`, which finds it by its record locator if the user may read it. The pages keep their view classes and url names, which
:func:`smarter.lib.manifest.record_locator.console_paths` reverses.
"""

from smarter.apps.dashboard.views.console_app import ConsoleAppView


class LLMHostDetailView(ConsoleAppView):
    """An LLMHost's manifest page: the single-page console's, at the path that Django served it at."""


class LLMHostComputeDetailView(ConsoleAppView):
    """An LLMHostCompute's manifest page: the single-page console's, at the path that Django served it at."""
