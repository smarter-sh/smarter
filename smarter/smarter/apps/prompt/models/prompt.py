"""Prompt model for the prompt app."""

from django.db import models

from smarter.apps.account.models import (
    MetaDataWithOwnershipModel,
    MetaDataWithOwnershipModelManager,
)
from smarter.apps.llmclient.models import LLMClient
from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.lib import logging
from smarter.lib.cache import cache_results
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
    llmclient = models.ForeignKey(LLMClient, on_delete=models.CASCADE, blank=False, null=False)
    ip_address = models.GenericIPAddressField(blank=False, null=False)
    user_agent = models.CharField(max_length=255, blank=False, null=False)
    url = models.URLField(blank=False, null=False)

    @property
    def is_billable_resource(self) -> bool:
        """
        Indicates whether the model instance is considered a billable resource.

        This property can be overridden in subclasses to specify which models are billable.
        By default, it returns False, indicating that the base TimestampedModel is not billable.

        :returns: True if the instance is billable, False otherwise.
        :rtype: bool
        """
        return True

    def __str__(self):
        # pylint: disable=E1136
        return f"{self.id} - {self.ip_address} - {self.url}"  # type: ignore[return]

    def delete(self, *args, **kwargs):
        if self.session_key:
            get_cached_prompt_by_session_key.invalidate(self.session_key)  # type: ignore[attr-defined]
        super().delete(*args, **kwargs)


@cache_results(timeout=smarter_settings.chat_cache_expiration or 300)
def get_cached_prompt_by_session_key(session_key: str) -> Prompt:
    """
    Return the Prompt of a chat session.

    Every prompt of a session looks up its Prompt, so it is cached. A missing Prompt
    raises, and so is never cached: PromptHelper creates it, and the next prompt of the
    session finds it.

    :param session_key: The chat session's key.
    :type session_key: str
    :returns: The session's Prompt.
    :rtype: Prompt
    :raises Prompt.DoesNotExist: If the session has no Prompt.
    """
    return Prompt.objects.select_related("llmclient").get(session_key=session_key)
