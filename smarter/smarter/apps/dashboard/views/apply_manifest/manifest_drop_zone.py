"""
Views for the manifest drop zone page.

This module provides a view that renders a drag-and-drop interface allowing
authenticated users to upload a manifest file and apply it to the Smarter
platform.

Classes:
    ManifestDropZoneView: Renders the manifest drag-and-drop upload page.

Example:
    Wire up the view in your URL configuration::

        from smarter.apps.dashboard.views.apply_manifest.manifest_drop_zone import ManifestDropZoneView

        urlpatterns = [
            path("apply-manifest/", ManifestDropZoneView.as_view(), name="manifest-drop-zone"),
        ]
"""

from typing import Any

from django.http import HttpRequest
from django.shortcuts import render

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.connection.urls import ConnectionReverseNames
from smarter.apps.plugin.urls import PluginReverseNames
from smarter.apps.prompt.urls import PromptReverseNames
from smarter.apps.provider.urls import ProviderReverseNames
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView

logger = logging.getLogger(__name__)


class ManifestDropZoneView(SmarterAuthenticatedNeverCachedWebView):
    """
    A simple view that renders a page with a manifest drop zone.

    for plugin development.
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{ManifestDropZoneView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def get_context(self) -> dict[str, Any]:
        """
        Provides context for enabling file drop zone functionality in the dashboard.

        This context processor injects a variable into the template context that can
        be used to enable or disable file drop zone features in the dashboard interface.
        This is useful for enhancing user experience by allowing drag-and-drop file uploads.

        :return: A dictionary containing the file drop zone context variable.
        :rtype: dict
        """

        @cache_results()
        def get_cached_file_drop_zone_context() -> dict[str, Any]:

            retval = {
                "drop_zone": {
                    "file_drop_zone_enabled": smarter_settings.file_drop_zone_enabled,
                    "api_apply_path": reverse(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.apply),
                    "workbench_list_path": reverse(PromptReverseNames.namespace, PromptReverseNames.listview),
                    "plugin_list_path": reverse(PluginReverseNames.namespace, PluginReverseNames.listview),
                    "connection_list_path": reverse(ConnectionReverseNames.namespace, ConnectionReverseNames.listview),
                    "provider_list_path": reverse(ProviderReverseNames.namespace, ProviderReverseNames.listview),
                }
            }
            logger.debug(
                "%s.get_context() cached file drop zone context: %s",
                self.formatted_class_name,
                logging.formatted_json(retval),
            )
            return retval

        return get_cached_file_drop_zone_context()

    template_path = "prompt/manifest-apply.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        return render(request, self.template_path, context=self.get_context())
