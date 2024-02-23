# -*- coding: utf-8 -*-
"""Django application configuration for the hello_world app"""
from django.apps import AppConfig


class HelloWorldConfig(AppConfig):
    """HelloWorldConfig application configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.hello_world"
