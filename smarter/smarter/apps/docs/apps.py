"""This module is used to configure the Smarter docs app."""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    """AdminConfig class. This class is used to configure the Smarter docs app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.docs"
