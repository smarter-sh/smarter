"""Vectorstore app configuration."""

from django.apps import AppConfig


class VectorstoreConfig(AppConfig):
    """
    Configuration for the vectorstore app.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "vectorstore"
