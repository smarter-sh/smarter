"""LLMClientCustomDomain model."""

import re
from datetime import datetime
from typing import Optional

from django.db import models
from django.utils import timezone

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

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING])


VERIFIED_DOMAINS_CACHE_KEY = "LLMClientCustomDomain_llmclient_verified_custom_domains"


def custom_domain_name(domain_name: str) -> str:
    """
    The default resource name of a custom domain: its domain name in snake_case,.

    e.g. 'llmclient.example.com' -> 'llmclient_example_com'.
    """
    return re.sub(r"[^a-z0-9]+", "_", domain_name.lower()).strip("_")


class LLMClientCustomDomain(MetaDataWithOwnershipModel):
    """
    Represents a DNS host record for a customer account's LLMClient, linked to an AWS Hosted Zone.

    This model is used to manage custom domains for llmclients within the Smarter platform. Each instance
    of this model corresponds to a DNS host (subdomain) that is associated with a specific customer
    account and is managed through AWS Route 53 Hosted Zones.

    The primary purpose of this model is to enable customers to use their own branded domains for
    llmclient endpoints, rather than relying solely on default platform-provided domains. This allows
    for improved branding, trust, and integration with customer infrastructure.

    **Key Features**

    - Is owned by a :class:`UserProfile`, like every other Smarter resource, and so has a name,
      description, version, tags and annotations, and may be shared with the owner's account.
      Its default name is its domain name in snake_case.
    - Stores the AWS Hosted Zone ID for DNS management and automation.
    - Tracks the verification status of the domain, indicating whether DNS records have been correctly
      configured and validated.
    - Supports caching of verified domains for efficient lookup and validation across the platform.

    **Usage Scenarios**

    - When a customer wishes to deploy an llmclient at a custom subdomain (e.g., ``llmclient.example.com``),
      an instance of this model is created to represent and manage that domain.
    - The platform uses the AWS Hosted Zone ID to automate DNS record creation and validation as part
      of the llmclient deployment workflow.
    - ``verification_status`` tracks the domain through verification: Not Verified, Verifying,
      Verified or Failed. A domain is Verified when its NS records are delegated to its Route53
      hosted zone, and its AWS ACM TLS certificate is issued. ``verified_at`` records when, and ``verification_message`` the step that is
      blocking verification. Only verified domains are used for llmclient endpoints.

    **Integration**

    - This model is referenced by other llmclient-related models, such as :class:`LLMClient` and
      :class:`LLMClientCustomDomainDNS`, to provide a complete mapping between llmclients, their domains,
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

        # Create a new custom domain for an llmclient
        custom_domain = LLMClientCustomDomain.objects.create(
            user_profile=my_user_profile,
            aws_hosted_zone_id="Z1234567890ABCDEF",
            domain_name="llmclient.example.com",
        )

        # Retrieve all verified custom domains
        verified_domains = LLMClientCustomDomain.get_verified_domains()
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "LLMClient Custom Domains"
        unique_together = (
            "user_profile",
            "name",
        )

    objects: MetaDataWithOwnershipModelManager["LLMClientCustomDomain"] = MetaDataWithOwnershipModelManager()

    #: The AWS Hosted Zone ID associated with this custom domain. This ID is used for DNS management via AWS Route 53.
    #: Example: "Z1234567890ABCDEF"
    #: Blank until ``smarter deploy`` registers the domain with AWS.
    aws_hosted_zone_id = models.CharField(max_length=255, blank=True, default="")

    #: The custom domain name for the LLMClient. This should be a valid DNS hostname.
    #: Example: "llmclient.example.com"
    domain_name = models.CharField(max_length=255)

    class VerificationStatusChoices(models.TextChoices):
        """
        The verification status of a custom domain.

        Managed by the asynchronous :func:`~smarter.apps.llmclient.tasks.verify_custom_domain` task.
        """

        NOT_VERIFIED = "Not Verified", "Not Verified"
        VERIFYING = "Verifying", "Verifying"
        VERIFIED = "Verified", "Verified"
        FAILED = "Failed", "Failed"

    #: Where the custom domain is in verification. A domain is Verified when its NS records are
    #: delegated to its Route53 hosted zone, and its TLS certificate is issued.
    verification_status = models.CharField(
        max_length=32,
        choices=VerificationStatusChoices.choices,
        default=VerificationStatusChoices.NOT_VERIFIED,
    )

    #: When the custom domain was last verified, or None if it is not verified.
    verified_at = models.DateTimeField(blank=True, null=True)

    #: Why the custom domain is not verified yet, or why its verification failed: the verification
    #: step that is blocking it. Blank once it is verified.
    verification_message = models.CharField(max_length=1024, blank=True, default="")

    @property
    def is_verified(self) -> bool:
        """True if the custom domain is verified."""
        return self.verification_status == self.VerificationStatusChoices.VERIFIED

    def set_verification_status(self, status: str, message: str = "") -> None:
        """
        Save a new verification status, and when it is Verified, the time of verification.

        Invalidates the cached list of verified domains.

        :param status: One of :class:`VerificationStatusChoices`.
        :param message: Why the domain is not verified, if it is not.
        """
        verified_at: Optional[datetime] = None
        if status == self.VerificationStatusChoices.VERIFIED:
            verified_at = timezone.now()
            message = ""
        self.verification_status = status
        self.verified_at = verified_at
        self.verification_message = message[:1024]
        LLMClientCustomDomain.objects.filter(pk=self.pk).update(
            verification_status=self.verification_status,
            verified_at=self.verified_at,
            verification_message=self.verification_message,
        )
        cache.delete(VERIFIED_DOMAINS_CACHE_KEY)

    @classmethod
    def get_verified_domains(cls):
        """
        Get all verified custom domains from cache or database.

        :returns: List of verified domain names.
        :rtype: List[str]
        """
        # Try to get the list from cache
        cache_key = VERIFIED_DOMAINS_CACHE_KEY
        verified_domains = cache.get(cache_key)

        # If the list is not in cache, fetch it from the database
        if not verified_domains:
            verified_domains = list(
                cls.objects.filter(verification_status=cls.VerificationStatusChoices.VERIFIED).values_list(
                    "domain_name", flat=True
                )
            )
            cache.set(key=cache_key, value=verified_domains, timeout=smarter_settings.cache_expiration)
            if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                logger.debug("get_verified_domains() caching %s", cache_key)

        return verified_domains

    def save(self, *args, **kwargs):
        """
        Save the LLMClientCustomDomain instance, validating the domain name.

        A custom domain that has no name is named after its domain name.

        :raises ValidationError: If the domain name is not valid.

        :returns: None
        """
        if self.domain_name:
            SmarterValidator.validate_domain(self.domain_name)
            if not self.name:
                self.name = custom_domain_name(self.domain_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.domain_name) if self.domain_name else "undefined"


__all__ = [
    "custom_domain_name",
    "LLMClientCustomDomain",
]
