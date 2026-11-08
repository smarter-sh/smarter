"""
A Provider's manifest page, ``/provider/providers/<hashed id>/``, which the single-page console serves (ADR-035).

The console shows the resource's manifest in the manifest editor, from the dashboard's resource api,
:mod:`smarter.apps.dashboard.resource_detail`, which finds it by its record locator if the user may read it. The page
keeps its view class and url name, which :func:`smarter.lib.manifest.record_locator.console_paths` reverses.
"""

from smarter.apps.dashboard.views.console_app import ConsoleAppView


class ProviderDetailView(ConsoleAppView):
    """A Provider's manifest page: the single-page console's, at the path that Django served it at."""
