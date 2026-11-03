"""Plugin urls."""

from django.urls import path
from django.views import View
from rest_framework.request import Request

from .const import namespace
from .views import (
    PluginCloneView,
    PluginListView,
    PluginUploadView,
    PluginView,
)

app_name = namespace


class RequestRouter(View):
    """Http method-based request router."""

    def dispatch(self, request: Request, *args, **kwargs):
        """
        Send a POST to :class:`PluginView`, which creates a plugin, and any other method to :class:`PluginListView`.

        :param request: The request.
        :param args: Positional arguments from the url.
        :param kwargs: Keyword arguments from the url.
        :returns: The response of the view that handled the request.
        """
        if request and isinstance(request.method, str) and request.method.lower() == "post":
            return PluginView.as_view()(request, *args, **kwargs)
        return PluginListView.as_view()(request, *args, **kwargs)


urlpatterns = [
    path("", RequestRouter.as_view(), name="plugins_list_view"),
    path(
        "<int:plugin_id>/",
        PluginView.as_view(),
        name="plugin_view",
    ),
    path(
        "<int:plugin_id>/clone/<str:new_name>",
        PluginCloneView.as_view(),
        name="plugin_clone_view",
    ),
    path("upload/", PluginUploadView.as_view(), name="plugin_upload"),
]
