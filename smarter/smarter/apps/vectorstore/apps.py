"""Vectorstore app configuration."""

import logging

from django.apps import AppConfig

from .const import namespace as app_name

logger = logging.getLogger(__name__)


class VectorstoreConfig(AppConfig):
    """
    Configuration for the vectorstore app.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = f"smarter.apps.{app_name}"
    verbose_name = "Smarter Vectorstore"
