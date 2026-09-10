"""URLs for Smarter Api."""

from django.urls import include, path
from django.views.generic import RedirectView

from smarter.apps.api import urls

urlpatterns = [
    # Alias for 'console_home' so that templates shared with the web console
    # (e.g. error pages) can resolve this name regardless of which
    # django-hosts urlconf is active for the current request.
    path("", RedirectView.as_view(url="v1/", permanent=True), name="console_home"),
    path("", include(urls)),
]

__all__ = ["urlpatterns"]
