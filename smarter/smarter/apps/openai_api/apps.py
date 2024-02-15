# -*- coding: utf-8 -*-
"""Implements API endpoints for the OpenAI API."""
from django.apps import AppConfig


class OpenaiApiConfig(AppConfig):
    """Django application configuration for the OpenAI API."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.openai_api"
