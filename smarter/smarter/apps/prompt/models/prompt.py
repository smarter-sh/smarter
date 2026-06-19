"""Prompt model for the prompt app."""

from django.db import models

from smarter.apps.account.models import (
    MetaDataWithOwnershipModel,
    MetaDataWithOwnershipModelManager,
)
from smarter.apps.llm_client.models import LLMClient
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.lib import logging
from smarter.lib.cache import lazy_cache as cache
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING])


class Prompt(MetaDataWithOwnershipModel):
    """Prompt model."""

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "Prompts"
        unique_together = (SMARTER_CHAT_SESSION_KEY_NAME, "url")

    objects: MetaDataWithOwnershipModelManager["Prompt"] = MetaDataWithOwnershipModelManager()

    session_key = models.CharField(max_length=255, blank=False, null=False, unique=True)
    llm_client = models.ForeignKey(LLMClient, on_delete=models.CASCADE, blank=False, null=False)
    ip_address = models.GenericIPAddressField(blank=False, null=False)
    user_agent = models.CharField(max_length=255, blank=False, null=False)
    url = models.URLField(blank=False, null=False)

    def __str__(self):
        # pylint: disable=E1136
        return f"{self.id} - {self.ip_address} - {self.url}"  # type: ignore[return]

    def delete(self, *args, **kwargs):
        if self.session_key:
            cache.delete(self.session_key)
        super().delete(*args, **kwargs)
