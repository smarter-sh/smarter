# -*- coding: utf-8 -*-
"""URL configuration for smarter project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("hello-world/", include("smarter.apps.hello_world.urls")),
    path("", include("smarter.apps.web_platform.urls")),
    path("admin/", admin.site.urls),
    path("api/", include("smarter.apps.api.urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
