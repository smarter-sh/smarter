"""Plugin urls."""

from django.urls import path
from django.views import View

from .const import namespace
from .views import (
    AddPluginExamplesView,
    PluginCloneView,
    PluginListView,
    PluginUploadView,
    PluginView,
)


app_name = namespace


class RequestRouter(View):
    """http method-based request router."""

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() == "post":
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
    path(
        "add-example-plugins/<int:user_id>/",
        AddPluginExamplesView.as_view(),
        name="add_plugin_examples",
    ),
    path("upload/", PluginUploadView.as_view(), name="plugin_upload"),
]
