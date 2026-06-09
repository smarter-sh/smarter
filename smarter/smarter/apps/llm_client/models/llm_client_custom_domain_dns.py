"""All models for the OpenAI Function Calling API app."""

from django.db import models

from smarter.lib import logging
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .llm_client_custom_domain import LLMClientCustomDomain

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING])


class LLMClientCustomDomainDNS(TimestampedModel):
    """
    Represents a DNS record associated with a custom domain for a LLMClient within the Smarter platform.

    This model is responsible for storing and managing individual DNS records that are linked to a
    specific :class:`LLMClientCustomDomain`. Each instance of this model corresponds to a single DNS
    record, such as an A, CNAME, or TXT record, which is required for the proper operation and
    verification of an llm_client's custom domain.

    The primary use case for this model is to facilitate the automation and tracking of DNS
    configurations necessary for deploying llm_clients on customer-branded domains. By maintaining a
    record of all DNS entries related to an llm_client's custom domain, the platform can automate DNS
    verification, support trouble shooting, and ensure that all required DNS records are present and
    correctly configured.

    **Key Features**

    - Associates each DNS record with a specific :class:`LLMClientCustomDomain`.
    - Stores the record name, type (such as A, CNAME, TXT), value, and TTL (time-to-live).
    - Supports management of multiple DNS records per custom domain, enabling complex DNS setups.
    - Facilitates DNS verification workflows and integration with external DNS providers (e.g., AWS Route 53).

    **Usage Scenarios**

    - When deploying an llm_client to a custom domain, instances of this model are created to represent
      the required DNS records (e.g., for domain verification, routing, or certificate issuance).
    - The platform can query this model to retrieve all DNS records associated with a given custom domain,
      enabling automated checks and updates.
    - Used internally by deployment and verification processes to track the status and configuration
      of DNS records for each llm_client custom domain.

    **Integration**

    - Closely linked to :class:`LLMClientCustomDomain`, providing a one-to-many relationship between
      a custom domain and its DNS records.
    - Referenced by deployment, verification, and trouble shooting workflows within the Smarter platform.

    **Notes**

    - This model is intended for internal use and is not exposed directly to end users.
    - The record fields are validated to ensure compliance with DNS standards.
    - TTL defaults to 600 seconds but can be customized as needed for specific DNS requirements.

    **Example**

    .. code-block:: python

        # Create a new DNS record for an llm_client custom domain
        dns_record = LLMClientCustomDomainDNS.objects.create(
            custom_domain=my_custom_domain,
            record_name="_acme-challenge.llm_client.example.com",
            record_type="TXT",
            record_value="abc123xyz",
            record_ttl=600,
        )

        # Retrieve all DNS records for a custom domain
        records = LLMClientCustomDomainDNS.objects.filter(custom_domain=my_custom_domain)
    """

    class Meta:
        verbose_name_plural = "LLMClient Custom Domain DNS"

    #: The LLMClientCustomDomain that this DNS record is associated with.
    #: Example: LLMClientCustomDomain(id=1, domain="example.com")
    custom_domain = models.ForeignKey(LLMClientCustomDomain, on_delete=models.CASCADE)

    #: The name of the DNS record (e.g., "_acme-challenge.llm_client.example.com").
    #: Example: "_acme-challenge.llm_client.example.com"
    record_name = models.CharField(max_length=255)

    #: The type of DNS record (e.g., "A", "CNAME", "TXT").
    #: Example: "TXT"
    record_type = models.CharField(max_length=255)

    #: The value of the DNS record (e.g., "abc123xyz").
    #: Example: "abc123xyz"
    record_value = models.CharField(max_length=255)

    #: The time-to-live (TTL) for the DNS record, in seconds.
    #: Example: 600
    record_ttl = models.IntegerField(default=600, blank=True, null=True)


__all__ = ["LLMClientCustomDomainDNS"]
