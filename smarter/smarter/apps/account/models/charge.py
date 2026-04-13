"""Account Charge model."""

import logging

# django stuff
from django.conf import settings
from django.db import models

# our stuff
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from ..signals import new_charge_created
from .account import Account


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


CHARGE_TYPE_PROMPT_COMPLETION = "completion"
CHARGE_TYPE_PLUGIN = "plugin"
CHARGE_TYPE_TOOL = "tool"

CHARGE_TYPES = [
    (CHARGE_TYPE_PROMPT_COMPLETION, "Prompt Completion"),
    (CHARGE_TYPE_PLUGIN, "Plugin"),
    (CHARGE_TYPE_TOOL, "Tool"),
]

PROVIDER_OPENAI = "openai"
PROVIDER_METAAI = "metaai"
PROVIDER_GOOGLEAI = "googleai"

PROVIDERS = [
    (PROVIDER_OPENAI, "OpenAI"),
    (PROVIDER_METAAI, "Meta AI"),
    (PROVIDER_GOOGLEAI, "Google AI"),
]


class Charge(TimestampedModel):
    """
    Charge model for tracking periodic account billing events.

    Represents a single billing event for an account and user, including provider, charge type, token usage, and reference details.

    :param account: ForeignKey to :class:`Account`. The account being billed.
    :param user: ForeignKey to :class:`django.contrib.auth.models.User`. The user associated with the charge.
    :param session_key: String. Optional session identifier for the charge.
    :param provider: String. The LLM provider (e.g., OpenAI).
    :param charge_type: String. The type of charge (e.g., completion, plugin, tool).
    :param prompt_tokens: Integer. Number of prompt tokens used.
    :param completion_tokens: Integer. Number of completion tokens used.
    :param total_tokens: Integer. Total tokens used.
    :param model: String. The model name.
    :param reference: String. Reference identifier for the charge.

    .. note::

        A signal is emitted when a new charge is created, enabling downstream billing and analytics workflows.

    **Example usage**::

        charge = Charge.objects.create(
            account=account,
            user=user,
            provider="openai",
            charge_type="completion",
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
            model="gpt-4",
            reference="invoice-123"
        )

    .. seealso::

        :class:`Account`, :class:`LLMPrices`
    """

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="charge", null=False, blank=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="charge", null=False, blank=False
    )
    session_key = models.CharField(max_length=255, null=True, blank=True)
    provider = models.CharField(
        max_length=255,
        choices=PROVIDERS,
        default=PROVIDER_OPENAI,
    )
    charge_type = models.CharField(
        max_length=20,
        choices=CHARGE_TYPES,
        default=CHARGE_TYPE_PROMPT_COMPLETION,
    )
    prompt_tokens = models.IntegerField()
    completion_tokens = models.IntegerField()
    total_tokens = models.IntegerField()
    model = models.CharField(max_length=255)
    reference = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        super().save(*args, **kwargs)
        if is_new:
            logger.debug(
                "%s.save() New user charge created for %s %s. Sending signal.",
                formatted_text(__name__ + ".Charge()"),
                self.account.company_name,
                self.user.email,
            )
            new_charge_created.send(sender=self.__class__, charge=self)

    def __str__(self):
        return f"""{self.account.account_number} - {self.user.email} - {self.provider} - {self.charge_type} - {self.total_tokens}"""


__all__ = [
    "Charge",
    "CHARGE_TYPES",
    "PROVIDERS",
    "CHARGE_TYPE_PROMPT_COMPLETION",
    "CHARGE_TYPE_PLUGIN",
    "CHARGE_TYPE_TOOL",
]
