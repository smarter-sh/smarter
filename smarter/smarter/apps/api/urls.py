# -*- coding: utf-8 -*-
"""URL configuration for smarter project."""

from django.urls import include, path


urlpatterns = [
    path("v0/", include("smarter.apps.api.v0.urls")),
]
