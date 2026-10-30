"""URLs for Smarter Api."""

from django.urls import include, path
from django.views.generic import RedirectView

from smarter.apps.api import urls
from smarter.lib.django.http import error_handlers

urlpatterns = [
    # Alias for 'console_home' so that templates shared with the web console
    # (e.g. error pages) can resolve this name regardless of which
    # django-hosts urlconf is active for the current request.
    path("", RedirectView.as_view(url="v1/", permanent=True), name="console_home"),
    path("", include(urls)),
]

# Error pages that close their database connections. See smarter.lib.django.http.error_handlers.
handler400 = error_handlers.bad_request
handler403 = error_handlers.permission_denied
handler404 = error_handlers.page_not_found
handler500 = error_handlers.server_error

__all__ = ["urlpatterns", "handler400", "handler403", "handler404", "handler500"]
