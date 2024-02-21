# -*- coding: utf-8 -*-
"""Django app for the OpenAI Function Calling app."""
from django.apps import AppConfig


class OpenaiFunctionCallingConfig(AppConfig):
    """Django Config for the OpenAI Function Calling app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.openai_function_calling"
