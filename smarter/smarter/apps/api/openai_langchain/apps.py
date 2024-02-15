# -*- coding: utf-8 -*-
"""Django app configuration for the langchain app."""
from django.apps import AppConfig


class OpenaiLangchainConfig(AppConfig):
    """Django application configuration for the OpenAI LangChain app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.api.openai_langchain"
