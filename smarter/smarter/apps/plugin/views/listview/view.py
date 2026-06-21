# pylint: disable=W0613
"""
This module contains views to implement the React.

Plugin list view in the Smarter Dashboard.
"""

from django.conf import settings
from django.core.handlers.asgi import ASGIRequest
from django.shortcuts import render

from smarter.apps.plugin.models import PluginMeta
from smarter.lib import logging
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])


class PluginListView(SmarterAuthenticatedNeverCachedWebView):
    """
    Render the plugin list view for the Smarter Workbench web console.

    This view displays all plugins available to the authenticated user as cards, providing a quick overview and access to plugin details.

    :param request: Django HTTP request object.
    :type request: ASGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Additional keyword arguments.
    :type kwargs: dict

    :returns: Rendered HTML page with a card for each plugin, or a 404 error page if the user is not authenticated.
    :rtype: HttpResponse
    """

    template_path = "react/plugin-list.html"
    plugins: list[PluginMeta]

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{PluginListView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def get(self, request: ASGIRequest, *args, **kwargs):
        # pylint: disable=C0415
        from smarter.apps.plugin.urls import PluginReverseNames

        context = {
            "plugin_list": {
                "root_id": "smarter-plugin-list-root",
                "django_csrf_cookie_name": settings.CSRF_COOKIE_NAME,  # this is the CSRF token cookie that should be included in the header of the POST request from the frontend.
                "django_session_cookie_name": settings.SESSION_COOKIE_NAME,  # this is the Django session.
                "cookie_domain": settings.SESSION_COOKIE_DOMAIN,
                "plugin_list_api_url": reverse(PluginReverseNames.namespace, PluginReverseNames.listview_api_all),
                "react_debug_mode": switch_is_active(SmarterWaffleSwitches.ENABLE_REACTAPP_DEBUG_MODE),
            }
        }

        logger.debug(
            "%s.get() called for %s with args %s, kwargs %s with context %s",
            self.formatted_class_name,
            request,
            args,
            kwargs,
            logging.formatted_json(context),
        )
        return render(request, template_name=self.template_path, context=context)
