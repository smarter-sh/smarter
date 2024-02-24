# -*- coding: utf-8 -*-
"""URL configuration for smarter project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    # Django admin console
    path("admin/", admin.site.urls),
    path("hello-world/", include("smarter.apps.hello_world.urls")),
    # the web platform
    path("", include("smarter.apps.web_platform.urls")),
    # the API
    path("v0/", include("smarter.apps.api.v0_urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
