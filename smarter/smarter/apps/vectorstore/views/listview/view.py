# pylint: disable=W0613
"""
This module contains views to implement the React.

Vectorstore list view in the Smarter Dashboard.
"""

from django.conf import settings
from django.core.handlers.asgi import ASGIRequest
from django.shortcuts import render

from smarter.apps.vectorstore.models import VectorstoreMeta
from smarter.lib import logging
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.SECRET_LOGGING])


class VectorstoreListView(SmarterAuthenticatedNeverCachedWebView):
    """
    Render the vectorstore list view for the Smarter Workbench web console.

    This view displays all vectorstores available to the authenticated user as cards, providing a quick overview and access to vectorstore details.

    :param request: Django HTTP request object.
    :type request: ASGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Additional keyword arguments.
    :type kwargs: dict

    :returns: Rendered HTML page with a card for each vectorstore, or a 404 error page if the user is not authenticated.
    :rtype: HttpResponse
    """

    template_path = "react/vectorstore-list.html"
    vectorstores: list[VectorstoreMeta]

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{VectorstoreListView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def get(self, request: ASGIRequest, *args, **kwargs):
        # pylint: disable=C0415
        from smarter.apps.vectorstore.urls import VectorstoreReverseNames

        context = {
            "vectorstore_list": {
                "root_id": "smarter-vectorstore-list-root",
                "django_csrf_cookie_name": settings.CSRF_COOKIE_NAME,  # this is the CSRF token cookie that should be included in the header of the POST request from the frontend.
                "django_session_cookie_name": settings.SESSION_COOKIE_NAME,  # this is the Django session.
                "cookie_domain": settings.SESSION_COOKIE_DOMAIN,
                "vectorstore_list_api_url": reverse(
                    VectorstoreReverseNames.namespace, VectorstoreReverseNames.listview_api_all
                ),
                "react_debug_mode": switch_is_active(SmarterWaffleSwitches.ENABLE_REACTAPP_DEBUG_MODE),
                "smarter_request_id": self.generate_smarter_request_id(),
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
