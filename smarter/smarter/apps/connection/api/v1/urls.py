"""Connection API urls."""

from typing import Union

from django.urls import URLPattern, URLResolver

from .const import namespace

app_name = namespace

urlpatterns: list[Union[URLPattern, URLResolver]] = []
