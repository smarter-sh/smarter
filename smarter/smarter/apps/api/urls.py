# -*- coding: utf-8 -*-
"""URL configuration for smarter project."""

from django.urls import include, path
from django.views.generic import RedirectView


urlpatterns = [
    path("", RedirectView.as_view(url="/api/v0/", permanent=True)),
    path("v0/", include("smarter.apps.api.v0.urls")),
]
