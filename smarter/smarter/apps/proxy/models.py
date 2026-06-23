"""Proxy model."""

from django.db import models

from smarter.apps.account.models import (
    MetaDataWithOwnershipModel,
)
from smarter.apps.provider.models import Provider
from smarter.apps.secret.models import Secret
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROXY_LOGGING])


class Proxy(MetaDataWithOwnershipModel):
    """
    Proxy model representing an LLM Provider proxy configuration.

    what we need:

    - fk to a provider
    - the native api path
    - a connection to the provider's API
    - a way to generate Smarter API keys for this proxy
    - budget configuration
    """

    provider = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        related_name="proxies",
        help_text="The provider this proxy is associated with.",
    )
    path = models.CharField(
        max_length=255,
        unique=True,
        help_text="The native API path for this proxy.",
    )
    api_key_secret = models.ForeignKey(
        Secret,
        on_delete=models.CASCADE,
        related_name="proxies",
        help_text="The secret containing the API key for this proxy.",
    )


__all__ = [
    "Proxy",
]
