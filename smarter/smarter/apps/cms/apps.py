"""This module is used to configure the Smarter cms app."""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    """AdminConfig class. This class is used to configure the Smarter cms app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.cms"
