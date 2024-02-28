# -*- coding: utf-8 -*-
"""Django URL patterns for the chatapp"""
from django.urls import path

from .views import chatapp


urlpatterns = [
    path("", chatapp, name="chatapp"),
]
