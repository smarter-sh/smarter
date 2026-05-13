"""All models for the OpenAI Function Calling API app."""

from django.db import models

from smarter.apps.account.models import (
    MetaDataWithOwnershipModel,
    MetaDataWithOwnershipModelManager,
)
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.cache import lazy_cache as cache
from smarter.lib.django import waffle
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.CHATBOT_LOGGING])


class ChatBotCustomDomain(MetaDataWithOwnershipModel):
    """
    Represents a DNS host record for a customer account's ChatBot, linked to an AWS Hosted Zone.

    This model is used to manage custom domains for chatbots within the Smarter platform. Each instance
    of this model corresponds to a DNS host (subdomain) that is associated with a specific customer
    account and is managed through AWS Route 53 Hosted Zones.

    The primary purpose of this model is to enable customers to use their own branded domains for
    chatbot endpoints, rather than relying solely on default platform-provided domains. This allows
    for improved branding, trust, and integration with customer infrastructure.

    **Key Features**

    - Associates a custom domain with a customer :class:`Account`.
    - Stores the AWS Hosted Zone ID for DNS management and automation.
    - Tracks the verification status of the domain, indicating whether DNS records have been correctly
      configured and validated.
    - Supports caching of verified domains for efficient lookup and validation across the platform.

    **Usage Scenarios**

    - When a customer wishes to deploy a chatbot at a custom subdomain (e.g., ``chatbot.example.com``),
      an instance of this model is created to represent and manage that domain.
    - The platform uses the AWS Hosted Zone ID to automate DNS record creation and validation as part
      of the chatbot deployment workflow.
    - The ``is_verified`` field is updated as part of the DNS verification process, ensuring that only
      properly configured domains are used for chatbot endpoints.

    **Integration**

    - This model is referenced by other chatbot-related models, such as :class:`ChatBot` and
      :class:`ChatBotCustomDomainDNS`, to provide a complete mapping between chatbots, their domains,
      and DNS records.
    - The platform uses this model to enforce domain uniqueness and to prevent conflicts between
      customer accounts.

    **Notes**

    - The domain name must be a valid DNS hostname and is validated upon saving.
    - Caching is used to optimize the retrieval of verified domains, reducing database load and
      improving performance for domain-related checks.
    - This model is intended for internal use within the Smarter platform and is not exposed directly
      to end users.

    **Example**

    .. code-block:: python

        # Create a new custom domain for a chatbot
        custom_domain = ChatBotCustomDomain.objects.create(
            account=my_account,
            aws_hosted_zone_id="Z1234567890ABCDEF",
            domain_name="chatbot.example.com",
            is_verified=False,
        )

        # Retrieve all verified custom domains
        verified_domains = ChatBotCustomDomain.get_verified_domains()
    """

    class Meta:
        verbose_name_plural = "ChatBot Custom Domains"

    objects: MetaDataWithOwnershipModelManager["ChatBotCustomDomain"] = MetaDataWithOwnershipModelManager()

    #: The AWS Hosted Zone ID associated with this custom domain. This ID is used for DNS management via AWS Route 53.
    #: Example: "Z1234567890ABCDEF"
    aws_hosted_zone_id = models.CharField(max_length=255)

    #: The custom domain name for the ChatBot. This should be a valid DNS hostname.
    #: Example: "chatbot.example.com"
    domain_name = models.CharField(max_length=255)

    #: Indicates whether the custom domain has been verified. A verified domain has the correct DNS records configured.
    #: This is managed by the asynchronous ChatBot deployment process.
    #: Example: True
    is_verified = models.BooleanField(default=False, blank=True, null=True)

    @classmethod
    def get_verified_domains(cls):
        """
        Get all verified custom domains from cache or database.

        :returns: List of verified domain names.
        :rtype: List[str]
        """
        # Try to get the list from cache
        cache_key = "ChatBotCustomDomain_chatbot_verified_custom_domains"
        verified_domains = cache.get(cache_key)

        # If the list is not in cache, fetch it from the database
        if not verified_domains:
            verified_domains = list(cls.objects.filter(is_verified=True).values_list("domain_name", flat=True))
            cache.set(key=cache_key, value=verified_domains, timeout=smarter_settings.cache_expiration)
            if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                logger.debug("get_verified_domains() caching %s", cache_key)

        return verified_domains

    def save(self, *args, **kwargs):
        """
        Save the ChatBotCustomDomain instance, validating the domain name.

        :raises ValidationError: If the domain name is not valid.

        :returns: None
        """
        if self.domain_name:
            SmarterValidator.validate_domain(self.domain_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.domain_name) if self.domain_name else "undefined"


__all__ = [
    "ChatBotCustomDomain",
]
