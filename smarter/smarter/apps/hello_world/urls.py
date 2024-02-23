# -*- coding: utf-8 -*-
"""Django URL patterns for the hello_world app"""
from django.urls import path

from .views import hello_world


urlpatterns = [
    path("", hello_world, name="hello_world"),
]
