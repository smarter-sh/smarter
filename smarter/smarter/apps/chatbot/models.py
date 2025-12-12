# pylint: disable=W0613,C0115
"""All models for the OpenAI Function Calling API app."""
import logging
import warnings
from functools import cached_property
from typing import Any, List, Optional, Type
from urllib.parse import ParseResult, urljoin, urlparse

from django.core.exceptions import ValidationError
from django.db import models
from django.http import HttpRequest
from django.urls import reverse
from rest_framework import serializers

# our stuff
from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.serializers import AccountMiniSerializer
from smarter.apps.account.utils import (
    account_number_from_url,
    get_cached_account,
    get_cached_user_profile,
)
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.manifest.models.common.plugin.model import SAMPluginCommon
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.plugin.base import PluginBase
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_DEFAULT_CACHE_TIMEOUT
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.common.helpers.llm import get_date_time_string
from smarter.common.helpers.url_helpers import clean_url
from smarter.common.utils import rfc1034_compliant_str, smarter_build_absolute_uri
from smarter.lib import json
from smarter.lib.cache import cache_results
from smarter.lib.cache import lazy_cache as cache
from smarter.lib.django import waffle
from smarter.lib.django.model_helpers import TimestampedModel
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.loader import SAMLoader

from .signals import (
    chatbot_deploy_failed,
    chatbot_deploy_status_changed,
    chatbot_deployed,
    chatbot_dns_failed,
    chatbot_dns_verification_initiated,
    chatbot_dns_verification_status_changed,
    chatbot_dns_verified,
    chatbot_undeployed,
)


CACHE_PREFIX = "ChatBotHelper_"
API_VI_CHATBOT_NAMESPACE = "api:v1:chatbot"


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING) and level >= smarter_settings.log_level


def should_log_chatbot_helper(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_HELPER_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
chatbot_helper_logger = WaffleSwitchedLoggerWrapper(base_logger, should_log_chatbot_helper)


# -----------------------------------------------------------------------------
# ChatBot Models. These implement a ChatBot API for a customer account.
# -----------------------------------------------------------------------------
class ChatBotCustomDomain(TimestampedModel):
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

    #: The Smarter Account that owns this ChatBot custom domain.
    #: Example: Account(id=1, name="Acme Corp.")
    account = models.ForeignKey(Account, on_delete=models.CASCADE)

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
            cache.set(key=cache_key, value=verified_domains, timeout=SMARTER_DEFAULT_CACHE_TIMEOUT)
            if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                logger.info("get_verified_domains() caching %s", cache_key)

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


class ChatBotCustomDomainDNS(TimestampedModel):
    """
    Represents a DNS record associated with a custom domain for a ChatBot within the Smarter platform.

    This model is responsible for storing and managing individual DNS records that are linked to a
    specific :class:`ChatBotCustomDomain`. Each instance of this model corresponds to a single DNS
    record, such as an A, CNAME, or TXT record, which is required for the proper operation and
    verification of a chatbot's custom domain.

    The primary use case for this model is to facilitate the automation and tracking of DNS
    configurations necessary for deploying chatbots on customer-branded domains. By maintaining a
    record of all DNS entries related to a chatbot's custom domain, the platform can automate DNS
    verification, support troubleshooting, and ensure that all required DNS records are present and
    correctly configured.

    **Key Features**

    - Associates each DNS record with a specific :class:`ChatBotCustomDomain`.
    - Stores the record name, type (such as A, CNAME, TXT), value, and TTL (time-to-live).
    - Supports management of multiple DNS records per custom domain, enabling complex DNS setups.
    - Facilitates DNS verification workflows and integration with external DNS providers (e.g., AWS Route 53).

    **Usage Scenarios**

    - When deploying a chatbot to a custom domain, instances of this model are created to represent
      the required DNS records (e.g., for domain verification, routing, or certificate issuance).
    - The platform can query this model to retrieve all DNS records associated with a given custom domain,
      enabling automated checks and updates.
    - Used internally by deployment and verification processes to track the status and configuration
      of DNS records for each chatbot custom domain.

    **Integration**

    - Closely linked to :class:`ChatBotCustomDomain`, providing a one-to-many relationship between
      a custom domain and its DNS records.
    - Referenced by deployment, verification, and troubleshooting workflows within the Smarter platform.

    **Notes**

    - This model is intended for internal use and is not exposed directly to end users.
    - The record fields are validated to ensure compliance with DNS standards.
    - TTL defaults to 600 seconds but can be customized as needed for specific DNS requirements.

    **Example**

    .. code-block:: python

        # Create a new DNS record for a chatbot custom domain
        dns_record = ChatBotCustomDomainDNS.objects.create(
            custom_domain=my_custom_domain,
            record_name="_acme-challenge.chatbot.example.com",
            record_type="TXT",
            record_value="abc123xyz",
            record_ttl=600,
        )

        # Retrieve all DNS records for a custom domain
        records = ChatBotCustomDomainDNS.objects.filter(custom_domain=my_custom_domain)
    """

    class Meta:
        verbose_name_plural = "ChatBot Custom Domain DNS"

    #: The ChatBotCustomDomain that this DNS record is associated with.
    #: Example: ChatBotCustomDomain(id=1, domain="example.com")
    custom_domain = models.ForeignKey(ChatBotCustomDomain, on_delete=models.CASCADE)

    #: The name of the DNS record (e.g., "_acme-challenge.chatbot.example.com").
    #: Example: "_acme-challenge.chatbot.example.com"
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


def validate_provider(value):
    """
    Validate that the provider is in the list of valid chat providers.

    :param value: The provider value to validate.
    :raises ValidationError: If the provider is not valid.

    :returns: None
    """
    # pylint: disable=C0415
    from smarter.apps.prompt.providers.providers import chat_providers

    if not value in chat_providers.all:
        raise ValidationError(
            "%(value)s is not a valid provider. Valid providers are: %(providers)s",
            params={"value": value, "providers": str(chat_providers.all)},
        )


class ChatBot(TimestampedModel):
    """
    Implements the ChatBot API model for a customer account.

    This Django model represents a chatbot instance associated with a specific customer account.
    It provides configuration, deployment status, domain management, and API endpoint properties
    for each chatbot. The model supports multiple modes of operation (sandbox, custom, default),
    DNS verification, TLS certificate management, and integration with external providers.

    **Key Features**

    - Associates each chatbot with a customer :class:`Account`.
    - Supports custom domains and DNS verification via :class:`ChatBotCustomDomain`.
    - Tracks deployment status, TLS certificate issuance, and DNS verification.
    - Configures default provider, model, system role, temperature, and max tokens.
    - Provides properties for generating RFC 1034-compliant names, hosts, and URLs.
    - Supports sandbox, default, and custom domain modes.
    - Integrates with Django signals for deployment and verification events.
    - Serializes chatbot configuration for API and frontend consumption.

    **Usage Example**

    .. code-block:: python

        chatbot = ChatBot.objects.get(account=my_account, name="example")
        if chatbot.ready():
            print(chatbot.url_chatbot)

    **Signals**

    - Emits signals on deployment, DNS verification, and certificate status changes.

    **See Also**

    - :class:`ChatBotCustomDomain`
    - :class:`ChatBotCustomDomainDNS`
    - :class:`ChatBotPlugin`
    - :class:`ChatBotAPIKey`
    - :class:`ChatBotFunctions`
    - :class:`ChatBotRequests`

    :raises SmarterValueError: If invalid URLs or domains are provided.
    :raises ValidationError: If provider is not valid.
    """

    class Meta:
        verbose_name_plural = "ChatBots"
        unique_together = ("account", "name")

    class Modes:
        """
        ChatBot API Modes. Defines the operational mode of the ChatBot instance.
        Also affects the url scheme and hostname used to access the ChatBot API.
        """

        SANDBOX = "sandbox"
        CUSTOM = "custom"
        DEFAULT = "default"
        UNKNOWN = "unknown"

    class Schemes:
        """ChatBot API Schemes"""

        HTTP = "http"
        HTTPS = "https"

    class DnsVerificationStatusChoices(models.TextChoices):
        """
        DNS Verification Status Choices for ChatBot Custom Domains.
        This is managed by the asynchronous ChatBot deployment process.
        """

        VERIFYING = "Verifying", "Verifying"
        NOT_VERIFIED = "Not Verified", "Not Verified"
        VERIFIED = "Verified", "Verified"
        FAILED = "Failed", "Failed"

    class TlsCertificateIssuanceStatusChoices(models.TextChoices):
        """
        TLS Certificate Issuance Status Choices for ChatBot Custom Domains.
        This is managed by the asynchronous ChatBot deployment process.
        """

        NO_CERTIFICATE = "No Certificate", "No Certificate"
        REQUESTED = "Requested", "Requested"
        ISSUED = "Issued", "Issued"
        FAILED = "Failed", "Failed"

    #: The Smarter Account that owns this ChatBot.
    #: Example: Account(id=1, name="Acme Corp.")
    account = models.ForeignKey(Account, on_delete=models.CASCADE)

    #: The name of the ChatBot. This includes, for example, the slug in the
    #: deployed URL (e.g., 'my-chatbot' in 'my-chatbot.1234-5678-9012.api.example.com').
    #: The naming conventions follow RFC 1034 for DNS compliance.
    #: Example: 'my-chatbot'
    name = models.CharField(max_length=255)

    #: A brief description of the ChatBot. Less is more. Be concise.
    #: Example: "A helpful assistant for customer support."
    description = models.TextField(blank=True, null=True)

    #: The version of the ChatBot configuration or model. Use semantic versioning if applicable.
    #: Example: "1.0.0"
    version = models.CharField(max_length=255, blank=True, null=True)

    #: The subdomain DNS record associated with this ChatBot.
    #: Example: ChatBotCustomDomainDNS(id=1, domain="my-chatbot.example.com")
    subdomain = models.ForeignKey(ChatBotCustomDomainDNS, on_delete=models.CASCADE, blank=True, null=True)

    #: The custom domain associated with this ChatBot.
    #: Example: ChatBotCustomDomain(id=1, domain="example.com")
    custom_domain = models.ForeignKey(ChatBotCustomDomain, on_delete=models.CASCADE, blank=True, null=True)

    #: Indicates whether the ChatBot is deployed and accessible via its custom or default domain.
    #: Modifying this value triggers asynchronous deployment or undeployment processes.
    #: Example: True
    deployed = models.BooleanField(default=False, blank=True, null=True)

    #: The Smarter Provider for the ChatBot's language model.
    #: Example: "openai"
    provider = models.CharField(
        default=smarter_settings.llm_default_provider,
        max_length=255,
        blank=True,
        null=True,
        validators=[validate_provider],
    )

    #: The default language model used by the ChatBot.
    #: Example: "gpt-4o-mini"
    default_model = models.CharField(max_length=255, blank=True, null=True)

    #: The default system role prompt for the ChatBot.
    #: Example: "You are a helpful assistant."
    default_system_role = models.TextField(default=smarter_settings.llm_default_system_role, blank=True, null=True)

    #: The default temperature setting for the ChatBot's language model.
    #: Example: 0.7
    default_temperature = models.FloatField(default=smarter_settings.llm_default_temperature, blank=True, null=True)

    #: The default maximum tokens for the ChatBot's language model responses.
    #: Example: 1024
    default_max_tokens = models.IntegerField(default=smarter_settings.llm_default_max_tokens, blank=True, null=True)

    #: The ChatBot UI configuration fields. Appears in the title bar of the Smarter React ChatBot component.
    #: Example: "Stackademy Support Bot"
    app_name = models.CharField(default="chatbot", max_length=255, blank=True, null=True)

    #: The ChatBot UI configuration fields. Appears in the text input area placeholder.
    #: Example: "Stan"
    app_assistant = models.CharField(default="Smarter", max_length=255, blank=True, null=True)

    #: The ChatBot UI configuration fields. Appears in the welcome message area of the Smarter React ChatBot component.
    #: Example: "Welcome to Stackademy!"
    app_welcome_message = models.CharField(default="Welcome to the chatbot!", max_length=255, blank=True, null=True)

    #: The ChatBot UI configuration fields. Example prompts shown to the user in the Smarter React ChatBot component.
    #: Example: ["What AI courses do you offer?", "Is your program free?"]
    app_example_prompts = models.JSONField(default=list, blank=True, null=True)

    #: The ChatBot UI configuration fields. Placeholder text in the chat input area.
    #: Example: "Ask me anything about Stackademy..."
    app_placeholder = models.CharField(default="Type something here...", max_length=255, blank=True, null=True)

    #: The ChatBot UI configuration fields. URL to the app information button in the top-right
    #: of the Smarter React ChatBot component.
    #: Example: "https://smarter.sh"
    app_info_url = models.URLField(default="https://smarter.sh", blank=True, null=True)

    #: The ChatBot UI configuration fields. URL to the app background image in the Smarter React ChatBot component.
    #: Example: "https://cdn.platform.smarter.sh/chat-ui/background.png"
    app_background_image_url = models.URLField(blank=True, null=True)

    #: The ChatBot UI configuration fields. URL to the app logo image in the Smarter React ChatBot component.
    #: Example: "https://cdn.platform.smarter.sh/chat-ui/logo.png"
    app_logo_url = models.URLField(blank=True, null=True)

    #: The ChatBot UI configuration fields. Enables or disables file attachment feature in the Smarter React ChatBot component.
    #: Example: True
    app_file_attachment = models.BooleanField(default=False, blank=True, null=True)

    # : The DNS verification status of the ChatBot's custom domain. This is part of the deployment process and is managed by
    # : the asynchronous ChatBot deployment workflow.
    # : Example: "Verified"
    dns_verification_status = models.CharField(
        max_length=255,
        default=DnsVerificationStatusChoices.NOT_VERIFIED,
        blank=True,
        null=True,
        choices=DnsVerificationStatusChoices.choices,
    )

    # : The TLS certificate issuance status of the ChatBot's custom domain. This is part of the deployment process and is managed by
    # : the asynchronous ChatBot deployment workflow.
    # : Example: "Issued"
    tls_certificate_issuance_status = models.CharField(
        max_length=255,
        default=TlsCertificateIssuanceStatusChoices.NO_CERTIFICATE,
        blank=True,
        null=True,
        choices=TlsCertificateIssuanceStatusChoices.choices,
    )

    def __str__(self):
        return self.url if self.url else "undefined"

    @property
    def rfc1034_compliant_name(self) -> str:
        """
        Returns a RFC 1034 compliant name for the ChatBot.

        - lower case
        - alphanumeric characters and hyphens only
        - starts and ends with an alphanumeric character
        - max length of 63 characters

        :returns: RFC 1034 compliant name
        :rtype: str
        """
        return rfc1034_compliant_str(self.name)

    @property
    def default_system_role_enhanced(self):
        """
        prepends a date/time string to the default_system_role

        example: "2024-06-01 12:00:00 System: You are a helpful assistant."

        :returns: enhanced system role string
        :rtype: str
        """
        return f"{get_date_time_string()}{self.default_system_role}"

    @property
    def default_host(self):
        """
        The default hostname for the ChatBot.
        Examples:

        - self.name: 'example'
        - self.account.account_number: '1234-5678-9012'
        - smarter_settings.environment_api_domain: 'alpha.api.example.com'

        example 'example.1234-5678-9012.alpha.api.example.com'

        :returns: default hostname
        :rtype: str
        """
        domain = (
            f"{self.rfc1034_compliant_name}.{self.account.account_number}.{smarter_settings.environment_api_domain}"
        )
        SmarterValidator.validate_domain(domain)
        return domain

    @property
    def default_url(self):
        """
        The default URL for the ChatBot.

        example 'https://example.1234-5678-9012.alpha.api.example.com'

        :returns: default URL
        :rtype: str
        """
        return SmarterValidator.urlify(self.default_host, environment=smarter_settings.environment)  # type: ignore[return-value]

    @property
    def custom_host(self):
        """
        The custom hostname for the ChatBot.

        Examples:

        - self.name: 'example'
        - self.custom_domain.domain_name: 'example.com'

        example 'example.example.com'

        :returns: custom hostname
        :rtype: str
        """
        if self.custom_domain and self.custom_domain.is_verified:
            domain = f"{self.rfc1034_compliant_name}.{self.custom_domain.domain_name}"
            SmarterValidator.validate_domain(domain)
            return domain
        return None

    @property
    def custom_url(self):
        """
        The custom URL for the ChatBot.

        example 'https://example.example.com'

        :returns: custom URL
        :rtype: str
        """
        if self.custom_host:
            return SmarterValidator.urlify(self.custom_host, environment=smarter_settings.environment)  # type: ignore[return-value]
        return None

    @property
    def sandbox_host(self):
        """
        The sandbox hostname for the ChatBot. This is the hostname that is
        used when the ChatBot is in sandbox mode. For example, when the
        ChatBot is being used in the Smarter Workbench.

        example 'alpha.platform.smarter.sh'

        :returns: sandbox hostname
        :rtype: str
        """
        return smarter_settings.environment_platform_domain

    @property
    def sandbox_url(self):
        """
        The sandbox URL for the ChatBot. This is the URL that is used when
        the ChatBot is in sandbox mode. For example, when the ChatBot is
        being used in the Smarter Workbench. maps to "<int:chatbot_id>/"

        example: 'https://alpha.platform.smarter.sh/api/v1/chatbots/1/'

        :returns: sandbox URL
        :rtype: str
        """
        path = reverse(f"{API_VI_CHATBOT_NAMESPACE}:chatbot_view", kwargs={"chatbot_id": self.id})  # type: ignore[arg-type]
        url = urljoin(smarter_settings.environment_url, path)
        url = SmarterValidator.urlify(url, environment=smarter_settings.environment)  # type: ignore[return-value]
        return url

    @property
    def hostname(self):
        """
        The hostname for the ChatBot depending on its deployment status.
        Returns either the custom hostname (if deployed), the default hostname, or the sandbox hostname.

        :returns: hostname
        :rtype: str
        """
        if self.deployed:
            return self.custom_host or self.default_host
        return self.sandbox_host

    @property
    def url(self):
        """
        The URL for the ChatBot depending on its deployment status.

        example: 'https://my-chatbot.1234-5678-9012.alpha.api.example.com' (custom, deployed)

        :returns: URL
        :rtype: str
        """
        if self.deployed:
            return self.custom_url or self.default_url
        return self.sandbox_url

    @property
    def url_chatbot(self):
        """
        The Smarter Api url returned by ChatConfigView.config() as the
        key, "url_chatbot". This url is consumed by React.js app for http
        requests on new prompts.

        maps to "<int:chatbot_id>/chat/"
        example: "http://localhost:8000/api/v1/chatbots/5174/chat/"

        :returns: URL for chatbot API
        :rtype: str
        """
        path = reverse(f"{API_VI_CHATBOT_NAMESPACE}:default_chatbot_api_view", kwargs={"chatbot_id": self.id})  # type: ignore[arg-type]

        url = urljoin(smarter_settings.environment_url, path)
        url = SmarterValidator.urlify(url, environment=smarter_settings.environment)  # type: ignore[return-value]
        if not isinstance(url, str):
            raise SmarterValueError("ChatBot.url_chatbot is not a valid string")

        return url

    @property
    def url_chat_config(self):
        """
        The Smarter Api url for the Chat config json dict.
        The React.js app requests this url during react app startup
        to retrieve the UI configuration for the chatbot.

        maps to "<int:chatbot_id>/config/"
        example: "http://localhost:8000/api/v1/chatbots/5174/config/"

        :returns: URL for chatbot config API
        :rtype: str
        """
        path = reverse(f"{API_VI_CHATBOT_NAMESPACE}:chat_config_view", kwargs={"chatbot_id": self.id})  # type: ignore[arg-type]
        url = urljoin(smarter_settings.environment_url, path)
        url = SmarterValidator.urlify(url, environment=smarter_settings.environment)  # type: ignore[return-value]
        return url

    @property
    def url_chatapp(self) -> str:
        """
        (Deprecated) The Smarter Api url for the ChatApp endpoint. This url is used by the React.js app
        to load the ChatApp web page.

        maps to "chat/"
        """
        warnings.warn(
            "ChatBot.url_chatapp is deprecated and will be removed in a future release.",
            DeprecationWarning,
            stacklevel=2,
        )
        if not isinstance(self.url, str):
            raise SmarterValueError("ChatBot.url is not a valid string")
        return urljoin(self.url, "chat/")

    def ready(self):
        """
        The readiness status of the ChatBot.

        A ChatBot is ready if it is its in sandbox mode, or, if it is:

        - deployed
        - has a verified DNS A record
        - has a valid, issued tls certificate.

        :returns: readiness status
        :rtype: bool
        """
        if isinstance(self.url, str) and self.mode(self.url) == self.Modes.SANDBOX:
            return True

        if self.dns_verification_status != self.DnsVerificationStatusChoices.VERIFIED:
            logger.warning(
                "ChatBot %s is not ready. DNS verification status is %s",
                self.rfc1034_compliant_name,
                self.dns_verification_status,
            )
            return False

        if self.tls_certificate_issuance_status != self.TlsCertificateIssuanceStatusChoices.ISSUED:
            logger.warning(
                "ChatBot %s is not ready. TLS certificate issuance status is %s",
                self.rfc1034_compliant_name,
                self.tls_certificate_issuance_status,
            )
            return False

        if not self.deployed:
            logger.warning("ChatBot %s is not ready. It is not deployed.", self.rfc1034_compliant_name)
            return False

        return True

    def mode(self, url: str) -> str:
        """
        Determine the mode of the ChatBot based on the provided URL.

        :param url: The URL to evaluate.
        :returns: The mode of the ChatBot (sandbox, custom, default, unknown).
        :rtype: str
        """
        logger.debug("mode: %s", url)
        if not url:
            return self.Modes.UNKNOWN
        SmarterValidator.validate_url(url)
        url = SmarterValidator.urlify(url, environment=smarter_settings.environment)  # type: ignore[return-value]
        parsed_url = urlparse(url)
        input_hostname = parsed_url.netloc

        # most likely case first when running in production, at scale.
        try:
            default_url = SmarterValidator.urlify(self.default_host, environment=smarter_settings.environment)  # type: ignore[return-value]
            if default_url:
                default_hostname = urlparse(default_url).netloc
                if default_hostname and input_hostname == default_hostname:
                    return self.Modes.DEFAULT
        except SmarterValueError:
            pass

        # workbench sandbox mode
        try:
            sandbox_url = SmarterValidator.urlify(self.sandbox_host, environment=smarter_settings.environment)  # type: ignore[return-value]
            if sandbox_url:
                sandbox_hostname = urlparse(sandbox_url).netloc
                if sandbox_hostname and input_hostname == sandbox_hostname:
                    return self.Modes.SANDBOX
        except SmarterValueError:
            pass

        # custom domain mode. Least likely case.
        try:
            custom_url = SmarterValidator.urlify(self.custom_host, environment=smarter_settings.environment)  # type: ignore[return-value]
            if custom_url:
                custom_hostname = urlparse(custom_url).netloc
                if custom_hostname and input_hostname == custom_hostname:
                    return self.Modes.CUSTOM
        except SmarterValueError:
            pass

        logger.error(
            "Invalid ChatBot url %s received for default_url: %s, sandbox_url: %s, custom_url: %a",
            url,
            self.default_url,
            self.sandbox_url,
            self.custom_url,
        )
        # default to default mode as a safety measure
        return self.Modes.UNKNOWN

    def save(self, *args, **kwargs):
        """
        Override save() to validate domain and send signals on status changes.

        :raises SmarterValueError: If invalid hostname is provided.

        :args: Positional arguments for the save method.
        :kwargs: Keyword arguments for the save method.
        :returns: None
        """
        is_new = self.pk is None
        SmarterValidator.validate_domain(self.hostname)
        super().save(*args, **kwargs)
        if is_new:
            if self.deployed:
                chatbot_deployed.send(sender=self.__class__, chatbot=self)
        else:
            orig = ChatBot.objects.get(pk=self.pk) if self.pk is not None else self
            if orig.dns_verification_status != self.dns_verification_status:
                chatbot_dns_verification_status_changed.send(sender=self.__class__, chatbot=self)
                chatbot_deploy_status_changed.send(sender=self.__class__, chatbot=self)
                if self.dns_verification_status == ChatBot.DnsVerificationStatusChoices.VERIFYING:
                    chatbot_dns_verification_initiated.send(sender=self.__class__, chatbot=self)
                if self.dns_verification_status == ChatBot.DnsVerificationStatusChoices.VERIFIED:
                    chatbot_dns_verified.send(sender=self.__class__, chatbot=self)
                if self.dns_verification_status == ChatBot.DnsVerificationStatusChoices.FAILED:
                    chatbot_dns_failed.send(sender=self.__class__, chatbot=self)
                    chatbot_deploy_failed.send(sender=self.__class__, chatbot=self)
            if self.deployed and not orig.deployed:
                chatbot_deployed.send(sender=self.__class__, chatbot=self)
            if not self.deployed and orig.deployed:
                chatbot_undeployed.send(sender=self.__class__, chatbot=self)


class ChatBotAPIKey(TimestampedModel):
    """
    Represents the mapping of API keys to ChatBot instances within the Smarter platform.

    .. important::

        If present, the ChatBot associated with this record will require Api Key authentication
        for all API requests. Otherwise, the ChatBot will allow anonymous unauthenticated access.

        See :class:`smarter.lib.drf.token_authentication.SmarterTokenAuthentication` .

    This model establishes a relationship between a ChatBot and its associated API keys,
    enabling secure authentication and authorization for API access. Each entry in this
    model links a specific ChatBot to a unique API key, allowing fine-grained control
    over which keys can interact with which chatbot instances.

    The ChatBotAPIKey model is essential for managing access to chatbot APIs, supporting
    use cases such as per-bot API key rotation, revocation, and auditing. By associating
    API keys with individual chatbots, the platform can enforce security policies and
    monitor usage at the chatbot level.

    Typical usage involves creating a ChatBotAPIKey instance whenever a new API key is
    provisioned for a chatbot, and querying this model to validate incoming requests
    against active keys.

    **Model Relationships**

    - Each ChatBotAPIKey is linked to one :class:`ChatBot` instance.
    - Each ChatBotAPIKey references one :class:`SmarterAuthToken` representing the API key.

    **Example**

    .. code-block:: python

        # Assign an API key to a chatbot
        api_key = SmarterAuthToken.objects.create(...)
        chatbot_api_key = ChatBotAPIKey.objects.create(chatbot=my_chatbot, api_key=api_key)

        # Query API keys for a chatbot
        keys = ChatBotAPIKey.objects.filter(chatbot=my_chatbot)

    **Notes**

    - API key activation and deactivation are managed via the SmarterAuthToken model.
    - This model supports auditing and access control for chatbot API endpoints.
    - Intended for internal use within the Smarter platform to secure chatbot APIs.
    """

    class Meta:
        verbose_name_plural = "ChatBot API Keys"

    #: The ChatBot instance associated with this API key.
    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE)

    #: The API key (SmarterAuthToken) associated with the ChatBot.
    api_key = models.ForeignKey(SmarterAuthToken, on_delete=models.CASCADE)


class ChatBotPlugin(TimestampedModel):
    """
    Represents the association between a ChatBot instance and its enabled plugins within the Smarter platform.

    This model establishes a many-to-one relationship, where each plugin entry is linked to a specific ChatBot
    and references metadata describing the plugin. By maintaining this mapping, the platform can manage which
    plugins are available to each chatbot, enabling extensibility and customization of chatbot capabilities.

    The ChatBotPlugin model supports use cases such as plugin activation, deactivation, and enumeration for
    individual chatbots. It is essential for scenarios where chatbots require additional functionality
    provided by external or internal plugins, such as integrations, enhanced processing, or custom behaviors.

    **Model Relationships**

    - Each ChatBotPlugin is linked to one :class:`ChatBot` instance.
    - Each ChatBotPlugin references one :class:`PluginMeta` instance, which contains metadata about the plugin.

    **Usage Example**

    .. code-block:: python

        # Add a plugin to a chatbot
        plugin_meta = PluginMeta.objects.get(name="weather")
        chatbot_plugin = ChatBotPlugin.objects.create(chatbot=my_chatbot, plugin_meta=plugin_meta)

        # List all plugins for a chatbot
        plugins = ChatBotPlugin.objects.filter(chatbot=my_chatbot)

    **Notes**

    - Plugin management and loading are handled via the PluginController and related infrastructure.
    - This model is intended for internal use to support dynamic extension of chatbot features.
    - Uniqueness is enforced for each (chatbot, plugin_meta) pair to prevent duplicate plugin assignments.
    """

    class Meta:
        verbose_name_plural = "ChatBot Plugins"
        unique_together = ("chatbot", "plugin_meta")

    #: The ChatBot instance associated with this plugin.
    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE)

    #: The metadata for the plugin associated with the ChatBot.
    plugin_meta = models.ForeignKey(PluginMeta, on_delete=models.CASCADE)

    def __str__(self):
        return f"{str(self.chatbot.url)} - {str(self.plugin_meta.name)}"

    @property
    def plugin(self) -> Optional[PluginBase]:
        """
        Returns the Plugin instance associated with this ChatBotPlugin.

        :returns: Plugin instance or None
        :rtype: Optional[PluginBase]
        """
        if not self.chatbot:
            return None
        admin_user = UserProfile.admin_for_account(self.chatbot.account)
        if admin_user is None:
            raise SmarterValueError("ChatBotPlugin.plugin() failed to find admin user for chatbot account")
        user_profile = get_cached_user_profile(admin_user)
        plugin_controller = PluginController(
            account=self.chatbot.account, user=admin_user, plugin_meta=self.plugin_meta, user_profile=user_profile
        )
        this_plugin = plugin_controller.plugin
        return this_plugin

    @classmethod
    def load(cls: Type["ChatBotPlugin"], chatbot: ChatBot, data) -> "ChatBotPlugin":
        """
        Load (aka import) a plugin from a data file in yaml or json format.

        :param chatbot: The ChatBot instance to associate with the plugin.
        :param data: The plugin manifest data in yaml or json format.
        :returns: The created ChatBotPlugin instance.
        :rtype: ChatBotPlugin

        See Also:

        - :py:class:`smarter.apps.plugin.manifest.controller.PluginController`
        - :py:class:`smarter.lib.manifest.loader.SAMLoader`
        """
        if not chatbot:
            return None
        admin_user = UserProfile.admin_for_account(chatbot.account)
        if admin_user is None:
            raise SmarterValueError("ChatBotPlugin.plugin() failed to find admin user for chatbot account")
        user_profile = get_cached_user_profile(admin_user)
        loader = SAMLoader(manifest=data)
        manifest = SAMPluginCommon(**loader.json_data)  # type: ignore[call-arg]
        plugin_controller = PluginController(
            account=chatbot.account, user=admin_user, user_profile=user_profile, manifest=manifest
        )
        plugin = plugin_controller.plugin
        if not plugin or plugin.plugin_meta is None:
            raise SmarterValueError("ChatBotPlugin.load() failed to load plugin from data file")
        return cls.objects.create(chatbot=chatbot, plugin_meta=plugin.plugin_meta)

    @classmethod
    def plugins(cls, chatbot: ChatBot) -> List[PluginBase]:
        """
        Returns a list of Plugin instances associated with the given ChatBot.

        :param chatbot: The ChatBot instance to retrieve plugins for.
        :returns: List of Plugin instances.
        :rtype: List[PluginBase]

        :raises SmarterValueError: If admin user for chatbot account is not found
                                   or if a plugin fails to load.

        See Also:

        - :py:class:`smarter.apps.plugin.controller.PluginController`
        """
        if not chatbot:
            return []
        chatbot_plugins = cls.objects.filter(chatbot=chatbot)
        admin_user = UserProfile.admin_for_account(chatbot.account)
        if admin_user is None:
            raise SmarterValueError("ChatBotPlugin.plugin() failed to find admin user for chatbot account")
        user_profile = get_cached_user_profile(admin_user)
        retval = []
        for chatbot_plugin in chatbot_plugins:
            plugin_controller = PluginController(
                account=chatbot.account,
                user=admin_user,
                plugin_meta=chatbot_plugin.plugin_meta,
                user_profile=user_profile,
            )
            if not plugin_controller or not plugin_controller.plugin:
                raise SmarterValueError(
                    f"ChatBotPlugin.plugins() failed to load plugin for {chatbot_plugin.plugin_meta.name}"
                )
            retval.append(plugin_controller.plugin)
        return retval

    @classmethod
    def plugins_json(cls, chatbot: ChatBot) -> List[dict]:
        retval = []
        for plugin in cls.plugins(chatbot):
            retval.append(plugin.to_json())
        return retval


class ChatBotFunctions(TimestampedModel):
    """
    Represents the set of callable functions that are available to a ChatBot instance within the Smarter platform.

    This model is used to define and manage the specific functions that a chatbot can access or invoke during its operation.
    Each record in this model links a chatbot to a named function, enabling fine-grained control over the chatbot's capabilities.
    The available functions are defined by a fixed set of choices, such as "weather", "news", "prices", and "math".

    By associating functions with chatbots, the platform allows for extensible and customizable chatbot behavior, supporting
    use cases where different chatbots require access to different sets of features or integrations. This model is essential
    for scenarios where chatbots need to perform actions, retrieve information, or interact with external APIs in a controlled
    and auditable manner.

    **Model Relationships**

    - Each ChatBotFunctions entry is linked to one :class:`ChatBot` instance.
    - Each entry specifies a function name from a predefined set of choices.

    **Usage Example**

    .. code-block:: python

        # Assign a function to a chatbot
        ChatBotFunctions.objects.create(chatbot=my_chatbot, name="weather")

        # List all functions available to a chatbot
        functions = ChatBotFunctions.objects.filter(chatbot=my_chatbot)

    **Notes**

    - The set of available functions is controlled by the ``CHOICES`` class attribute.
    - This model is intended for internal use to manage and audit chatbot capabilities.
    - Uniqueness is not enforced, so a chatbot may have multiple entries for the same function if needed.
    """

    class Meta:
        verbose_name_plural = "ChatBot Functions"

    CHOICES = [
        ("weather", "weather"),
        ("news", "news"),
        ("prices", "prices"),
        ("math", "math"),
    ]
    """
    The set of available function names that can be assigned to a ChatBot.

    See Also:

    - :func:`smarter.apps.prompt.functions.function_weather.get_current_weather`
    """

    #: The ChatBot instance associated with this function.
    #: Example: ChatBot(id=1, name="my-chatbot")
    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE)

    #: The name of the function available to the ChatBot.
    #: Example: "weather"
    name = models.CharField(max_length=255, choices=CHOICES, blank=True, null=True)

    @classmethod
    def choices_list(cls):
        return [item[0] for item in cls.CHOICES]


class ChatBotRequests(TimestampedModel):
    """
    Stores the request history for a ChatBot instance within the Smarter platform.

    This model is designed to record and manage all incoming requests made to a chatbot, providing a persistent audit trail
    of interactions for analysis, debugging, and reporting. Each record in this model captures the details of a single request,
    including the associated chatbot, the request payload, session information, and aggregation status.

    **Purpose and Usage**

    The ChatBotRequests model enables comprehensive tracking of chatbot usage and user interactions. By storing each request,
    the platform can support features such as:

    - Request analytics and reporting for chatbot performance and user engagement.
    - Debugging and troubleshooting of chatbot behavior by reviewing historical requests.
    - Session management, allowing grouping and correlation of requests within a user session.
    - Aggregation of requests for batch processing or summarization.

    **Model Relationships**

    - Each ChatBotRequests entry is linked to one :class:`ChatBot` instance, establishing a direct association between the request and the chatbot that handled it.

    **Notes**

    - This model is intended for internal use to support auditing, analytics, and operational monitoring of chatbot activity.
    - The request data is stored in JSON format to accommodate flexible and extensible payload structures.
    - Aggregation support allows for efficient handling of bulk or grouped requests, which may be relevant for advanced chatbot workflows.

    **Example Usage**

    .. code-block:: python

        # Record a new request for a chatbot
        ChatBotRequests.objects.create(
            chatbot=my_chatbot,
            request={"message": "Hello, chatbot!"},
            session_key="abc123",
            is_aggregation=False,
        )

        # Retrieve all requests for a specific chatbot
        requests = ChatBotRequests.objects.filter(chatbot=my_chatbot)

    See Also:

    - :mod:`smarter.apps.chatbot.tasks`

    """

    class Meta:
        verbose_name_plural = "ChatBot Requests History"

    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE)
    request = models.JSONField(blank=True, null=True)
    session_key = models.CharField(max_length=255, blank=True, null=True)
    is_aggregation = models.BooleanField(default=False, blank=True, null=True)


class ChatBotRequestsSerializer(serializers.ModelSerializer):

    class Meta:
        model = ChatBotRequests
        fields = (
            "id",
            "created_at",
            "updated_at",
            "request",
            "is_aggregation",
        )


class ChatBotSerializer(serializers.ModelSerializer):
    url_chatbot = serializers.ReadOnlyField()
    account = AccountMiniSerializer()

    class Meta:
        model = ChatBot
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Meta.fields = [
            field.name
            for field in self.Meta.model._meta.get_fields()
            if field.name not in ["chat", "chatbotapikey", "chatbotplugin", "chatbotfunctions", "chatbotrequests"]
        ]
        self.Meta.fields += ["url_chatbot", "account"]


class ChatBotCustomDomainSerializer(serializers.ModelSerializer):

    class Meta:
        model = ChatBotCustomDomain
        fields = "__all__"


@cache_results()
def get_cached_chatbot(
    chatbot_id: Optional[int] = None, name: Optional[str] = None, account: Optional[Account] = None
) -> ChatBot:
    """
    Returns the chatbot from the cache if it exists, otherwise
    it queries the database and caches the result.
    """
    chatbot: ChatBot

    if chatbot_id:
        chatbot = ChatBot.objects.get(id=chatbot_id)
    else:
        if name and account:
            chatbot = ChatBot.objects.get(name=name, account=account)

    return chatbot


class ChatBotHelper(SmarterRequestMixin):
    """
    Provides a mapping between URLs and their corresponding ChatBot models,
    abstracting URL parsing logic for reuse across the codebase.

    This helper class is designed to centralize and standardize the logic
    required to resolve a ChatBot instance from a given URL or request context.
    It is intended for use in various locations, including within this module,
    Django middleware, and view logic.

    The class also implements caching of ChatBot objects for specific URLs,
    reducing redundant parsing and database queries for repeated requests.

    **Supported URL Patterns**

    The following are examples of valid URLs that this helper can process:

    - **Authentication Optional URLs:**
        - ``https://example.3141-5926-5359.alpha.api.example.com/``
        - ``https://example.3141-5926-5359.alpha.api.example.com/config/``

    - **Authenticated URLs:**
        - ``https://alpha.api.example.com/smarter/example/``
        - ``https://example.smarter.sh/chatbot/``
        - ``https://alpha.api.example.com/workbench/1/``
        - ``https://alpha.api.example.com/workbench/example/``

    - **Legacy (pre v0.12) URLs:**
        - ``https://alpha.api.example.com/chatbots/1/``
        - ``https://alpha.api.example.com/chatbots/example/``

    **Features**

    - Abstracts and encapsulates URL parsing and ChatBot resolution logic.
    - Provides a consistent interface for retrieving ChatBot instances from URLs.
    - Caches ChatBot objects to avoid redundant lookups.
    - Supports both authenticated and unauthenticated URL patterns.
    - Handles legacy URL formats for backward compatibility.

    **Usage**

    This class is typically instantiated with a Django ``HttpRequest`` object.
    It can then be used to access the resolved ChatBot instance and related
    metadata, such as the associated account, chatbot ID, and custom domain.

    Example::

        helper = ChatBotHelper(request)
        chatbot = helper.chatbot
        if helper.is_valid:
            # Proceed with chatbot logic

    :param request: The Django HttpRequest object containing the URL and user context.
    :type request: django.http.HttpRequest
    :param args: Additional positional arguments.
    :param kwargs: Additional keyword arguments, such as 'chatbot', 'chatbot_custom_domain', etc.

    :raises SmarterConfigurationError: If the helper cannot resolve a valid ChatBot instance.

    .. note::
        This class is intended for internal use within the Smarter platform and
        should not be used directly in user-facing code without proper validation.
    """

    __slots__ = (
        "_chatbot",
        "_chatbot_custom_domain",
        "_chatbot_requests",
        "_chatbot_id",
        "_name",
        "_err",
    )

    @property
    def formatted_class_name(self) -> str:
        """
        Get the formatted class name for this instance of ChatBotHelper.

        :returns: The formatted class name as a string, including the parent class name.
        :rtype: str

        This property returns a string representation of the class name,
        formatted to include the parent class's formatted name and the
        ``ChatBotHelper`` class. This is useful for logging and debugging
        purposes, as it provides a clear and consistent identifier for
        instances of this helper class.

        Example
        -------
        >>> helper = ChatBotHelper(request)
        >>> helper.formatted_class_name
        'SmarterRequestMixin.ChatBotHelper()'
        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.ChatBotHelper()"

    def __init__(self, request: HttpRequest, *args, **kwargs):
        """
        Initializes the ChatBotHelper instance.

        :param request: The Django HttpRequest object.
        :type request: django.http.HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        """
        self._instance_id = id(self)
        self._chatbot: Optional[ChatBot] = kwargs.get("chatbot")
        self._chatbot_custom_domain: Optional[ChatBotCustomDomain] = kwargs.get("chatbot_custom_domain")
        self._chatbot_requests: Optional[ChatBotRequests] = kwargs.get("chatbot_requests")
        self._err: Optional[str] = kwargs.get("err")
        self._chatbot_id: Optional[int] = kwargs.get("chatbot_id")
        self._name: Optional[str] = kwargs.get("name")

        # initializations that depend on the superclass
        super().__init__(request, *args, **kwargs)
        self._chatbot_id = self._chatbot_id or self.smarter_request_chatbot_id
        self._name = self._name or self.smarter_request_chatbot_name

        if not self.is_chatbot:
            self._err = f"ChatBotHelper.__init__() not a chatbot. Quitting. {self.url}"
            logger.debug(self._err)
            return None

        chatbot_helper_logger.info(
            "%s.__init__() %s is a chatbot. url=%s, name=%s, account=%s",
            self.formatted_class_name,
            self._instance_id,
            self.url,
            self.name,
            self.account,
        )

        if not self.user or not self.user.is_authenticated:
            logger.warning("ChatBotHelper.__init__() %s called with unauthenticated request", self._instance_id)
        if not self.account:
            logger.warning("ChatBotHelper.__init__() %s called with no account", self._instance_id)
        if not isinstance(self.name, str):
            logger.warning(
                "ChatBotHelper.__init__() %s did not find a name for the chatbot.",
                self._instance_id,
            )

        chatbot_helper_logger.info(
            f"__init__() {self._instance_id} url={ self.url } name={ self.name } chatbot_id={ self.chatbot_id } user={ self.user } account={ self.account }."
        )
        if not isinstance(self.chatbot, ChatBot):
            if self.account and self._name:
                self._chatbot = self._chatbot or get_cached_chatbot(account=self.account, name=self._name)
        if not isinstance(self._chatbot, ChatBot):
            logger.warning(
                "ChatBotHelper.__init__() %s did not find a ChatBot for url=%s, name=%s, chatbot_id=%s, account=%s",
                self._instance_id,
                self.url,
                self.name,
                self.chatbot_id,
                self.account,
            )

        if self.is_chatbothelper_ready:
            self.helper_logger(
                f"__init__() {self._instance_id} initialized self.chatbot={self.chatbot} from account and name"
            )
            chatbot_helper_logger.info(
                "%s.__init__() %s initialized with url=%s, name=%s, chatbot_id=%s, user=%s, account=%s, session_key=%s",
                self.formatted_class_name,
                self._instance_id,
                self.url if self.url else "undefined",
                self.name,
                self.chatbot_id,
                self.user,
                self.account,
                self.session_key,
            )
            return None

        raise SmarterConfigurationError(
            f"ChatBotHelper.__init__() {self._instance_id} failed to initialize ChatBot from url={self.url}, name={self.name}, chatbot_id={self.chatbot_id}. This is a bug in the code, please report it.",
        )

    def __str__(self):
        return str(self.chatbot) if self._chatbot else "undefined"

    @property
    def account(self) -> Optional[Account]:
        """
        Return the associated :class:`Account` for this ChatBotHelper instance,
        optionally overriding the default account based on the account number
        parsed from the URL, if available.

        If the URL contains an account number (for example,
        ``http://education.3141-5926-5359.api.localhost:8000/config/``),
        this method will attempt to retrieve and return the corresponding
        cached Account object. If no account number is found in the URL,
        the default account from the superclass is returned.

        :returns: The resolved :class:`Account` instance, or ``None`` if not found.
        :rtype: Optional[Account]
        """
        account_number = account_number_from_url(self.url)
        if account_number:
            chatbot_helper_logger.info("overriding account with account_number from named url: %s", self.url)
            return get_cached_account(account_number=account_number)  # type: ignore[return-value]

        # from the super()
        return self._account

    @property
    def chatbot_id(self) -> Optional[int]:
        """
        Returns the :attr:`ChatBot.id` for this ChatBotHelper instance.

        This property attempts to resolve the ChatBot's unique integer ID using several strategies:

        1. If a chatbot ID was provided at initialization, it is returned immediately.
        2. If a ChatBot object is already cached, its ID is returned.
        3. If the parent :class:`SmarterRequestMixin` provides a chatbot ID (e.g., parsed from the URL), it is used.
        4. If both a chatbot name and account are available, attempts to resolve and cache the ChatBot object and its ID.

        :returns: The resolved ChatBot ID, or ``None`` if not found.
        :rtype: Optional[int]
        """
        # check for a value passed in
        if self._chatbot_id:
            return self._chatbot_id

        # check for a chatbot object
        if self._chatbot:
            self._chatbot_id = self.chatbot.id  # type: ignore[return-value]
            return self._chatbot_id

        # check SmarterRequestMixin for a chatbot_id derived from the  url
        self._chatbot_id = super().smarter_request_chatbot_id
        if self._chatbot_id:
            return self._chatbot_id

        if self.chatbot_name and self.account:
            self._chatbot = get_cached_chatbot(name=self.chatbot_name, account=self.account)
            self.helper_logger(
                f"chatbot_id() initialized self.chatbot_id={self.chatbot_id} from name={ self.chatbot_name } and account={ self.account }"
            )
            return self._chatbot_id

        return self._chatbot_id

    @chatbot_id.setter
    def chatbot_id(self, chatbot_id: int):
        self._chatbot_id = chatbot_id
        chatbot = get_cached_chatbot(chatbot_id=self.chatbot_id)
        if chatbot and chatbot.account != self.account:
            raise SmarterValueError("ChatBotHelper.chatbot_id setter: chatbot.account does not match self.account")
        self._chatbot = chatbot
        if self._chatbot:
            self.helper_logger(f"@chatbot_id.setter initialized self.chatbot_id={self.chatbot_id} from chatbot_id")

    @property
    def chatbot_name(self) -> Optional[str]:
        """
        Returns the ChatBot.name for the ChatBotHelper.
        """
        return self.name

    @property
    def name(self) -> Optional[str]:
        """
        Returns the name of the chatbot.

        This property attempts to resolve the chatbot's name using several strategies, in order of precedence:

        1. ``self._name``: The name assigned during initialization, if available.
        2. ``self.chatbot.name``: The name attribute of the resolved ChatBot instance, if present.
        3. ``self.subdomain``: If the URL is a named chatbot URL (i.e., ``is_chatbot_named_url`` is True), the subdomain is used as the name.
        4. Path slug: If the URL is a sandbox chatbot URL (i.e., ``is_chatbot_sandbox_url`` is True), the path slug is used as the name.

        :returns: The resolved chatbot name, or ``None`` if not found.
        :rtype: Optional[str]
        """
        if self._chatbot:
            self._name = self._chatbot.name

        if self._name:
            return self._name

    @property
    def rfc1034_compliant_name(self) -> Optional[str]:
        """
        Returns a URL-friendly name for the chatbot.

        This is a convenience property that returns a RFC 1034 compliant name for the chatbot.

        Examples
        --------
        .. code-block:: python

            self.name  # 'Example ChatBot 1'
            self.rfc1034_compliant_name  # 'example-chatbot-1'

        :returns: The RFC 1034 compliant name for the chatbot, or ``None`` if not available.
        :rtype: Optional[str]
        """
        if self._chatbot:
            return self._chatbot.rfc1034_compliant_name
        return None

    @property
    def is_chatbothelper_ready(self) -> bool:
        """
        Returns ``True`` if the ChatBotHelper is ready to be used.

        This is a convenience property that checks if the ChatBotHelper
        is initialized and has a valid :class:`ChatBot` instance.

        :returns: ``True`` if the helper is initialized and has a valid ChatBot, otherwise ``False``.
        :rtype: bool
        """
        if not isinstance(self._chatbot, ChatBot):
            self._err = f"{self.formatted_class_name}.is_chatbothelper_ready() {self._instance_id} returning false because ChatBot is not initialized. url={self._url}"
            logger.debug(self._err)
            return False
        return True

    @property
    def ready(self) -> bool:
        """
        Returns ``True`` if the ChatBotHelper and its ChatBot are ready to be used

        :returns: ``True`` if both the helper and ChatBot are ready, otherwise ``False``.
        :rtype: bool
        """
        retval = bool(super().ready)
        if not retval:
            self._err = f"{self.formatted_class_name}.ready() {self._instance_id} returning false because ChatBot is not initialized. url={self._url}"
            logger.debug(self._err)
        return retval and self.is_chatbothelper_ready

    def to_json(self) -> dict[str, Any]:
        """
        Serialize the ChatBotHelper to a dictionary.

        This method returns a dictionary representation of the ChatBotHelper instance,
        including key metadata and related objects such as the chatbot, account, and custom domain.

        :returns: A dictionary containing the serialized state of the ChatBotHelper.
        :rtype: dict[str, Any]
        """
        return {
            "ready": self.ready,
            "name": self.name,
            "api_host": self.api_host,
            "chatbot_id": self.chatbot_id,
            "chatbot_name": self.chatbot_name,
            "chatbot_custom_domain": (
                ChatBotCustomDomainSerializer(self.chatbot_custom_domain) if self.chatbot_custom_domain else None
            ),
            "environment_api_domain": smarter_settings.environment_api_domain,
            "err": self._err,
            "is_custom_domain": self.is_custom_domain,
            "is_deployed": self.is_deployed,
            "is_valid": self.is_valid,
            "is_authentication_required": self.is_authentication_required,
            "chatbot": ChatBotSerializer(self.chatbot).data if self.chatbot else None,
            **super().to_json(),
        }

    @property
    def api_host(self) -> Optional[str]:
        """
        Returns the API host for a ChatBot API URL.

        This property extracts and returns the API host component from the chatbot URL,
        supporting named, sandbox, and custom domain URLs.

        Examples
        --------
        Named URL:
            - ``https://hr.3141-5926-5359.alpha.api.example.com/chatbot/``
              returns ``'alpha.api.example.com'``

        Sandbox URL:
            - ``http://api.localhost:8000/api/v1/chatbots/1/chat/``
              returns ``'api.localhost:8000'``

        Custom domain URL:
            - ``https://hr.smarter.sh/chatbot/``
              returns ``'hr.smarter.sh'``

        :returns: The API host as a string, or ``None`` if not found.
        :rtype: Optional[str]
        """
        if not self.smarter_request:
            return None
        if not self.qualified_request:
            return None
        if self.is_smarter_api and isinstance(self._url, ParseResult):
            return self._url.netloc
        if self.is_custom_domain and isinstance(self._url, ParseResult):
            # example: hr.bots.example.com
            return self._url.netloc
        return smarter_settings.environment_api_domain

    @property
    def is_deployed(self) -> bool:
        return self.chatbot.deployed if self.chatbot else False  # type: ignore[return-value]

    @property
    def is_valid(self) -> bool:
        """
        Validates whether the ChatBot is in a ready state,
        and if it is usable for making API calls.

        :returns: ``True`` if the ChatBot is valid and ready, otherwise ``False``.
        :rtype: bool
        """
        if not self.ready:
            self._err = f"is_valid() returning false because ChatBotHelper is not in a ready state: {self._url}"
            return False
        if self.is_authentication_required:
            if not self.user:
                self._err = f"is_valid() returning false because {self.name} chatbot requires authentication but user is unassigned"
                return False
            if not self.user.is_authenticated:
                self._err = f"is_valid() returning false because {self.name} chatbot requires authentication but user {self.user.username} is not authenticated"
                return False
        return True

    @cached_property
    def is_authentication_required(self) -> bool:
        """
        Determines if authentication is required to access the ChatBot.

        :returns: ``True`` if authentication is required, otherwise ``False``.
        :rtype: bool
        """
        if self.is_chatbot_sandbox_url:
            return True

        if ChatBotAPIKey.objects.filter(chatbot=self.chatbot, api_key__is_active=True).exists():
            return True
        return False

    @property
    def chatbot(self) -> Optional[ChatBot]:
        """
        Returns a lazy instance of the ChatBot.

        Examples
        --------
        - https://hr.3141-5926-5359.alpha.api.example.com/chatbot/
          returns ChatBot(name='hr', account=Account(...))

        :returns: The ChatBot instance, or ``None`` if not found.
        :rtype: Optional[ChatBot]
        """
        if self._chatbot:
            return self._chatbot

        # cheapest possibility
        if self._chatbot_id:
            self._chatbot = get_cached_chatbot(chatbot_id=self.chatbot_id)
            self.helper_logger(f"initialized chatbot {self._chatbot} from chatbot_id {self.chatbot_id}")
            return self._chatbot

        # our expected case
        if self.account and self.name:
            try:
                self._chatbot = get_cached_chatbot(account=self.account, name=self.name)
                self.helper_logger(
                    f"initialized chatbot {self._chatbot} from account {self.account} and name {self.name}"
                )
                return self._chatbot
            except ChatBot.DoesNotExist:
                logger.error(
                    "ChatBotHelper.chatbot() did not find chatbot for account: %s name: %s", self.account, self.name
                )

        return self._chatbot

    @property
    def is_custom_domain(self) -> bool:
        """
        Returns ``True`` if the ChatBot is using a custom domain.

        :returns: ``True`` if a custom domain is configured, otherwise ``False``.
        :rtype: bool
        """
        return self._chatbot_custom_domain is not None

    @property
    def chatbot_custom_domain(self) -> Optional[ChatBotCustomDomain]:
        """
        Returns a lazy instance of the ChatBotCustomDomain.

        Examples
        --------
        - ``https://hr.smarter.sh/chatbot/``
          returns ``ChatBotCustomDomain(domain_name='smarter.sh')``

        :returns: The ChatBotCustomDomain instance, or ``None`` if not found.
        :rtype: Optional[ChatBotCustomDomain]
        """
        if self._chatbot_custom_domain:
            return self._chatbot_custom_domain

        if not self._url:
            return None

        if self.is_chatbot_sandbox_url:
            # sandbox urls do not have a custom domain
            return None

        if self.is_default_domain:
            # default domain is not a custom domain
            return None

        if self.is_smarter_api:
            # smarter api urls do not have a custom domain
            return None

        try:
            self._chatbot_custom_domain = ChatBotCustomDomain.objects.get(domain_name=self.api_host)
        except ChatBotCustomDomain.DoesNotExist:
            return None

        return self._chatbot_custom_domain

    def helper_logger(self, message: str):
        """
        Create a log entry.

        This method writes an informational log entry using the
        :data:`chatbot_helper_logger`, including the formatted class name
        and the provided message.

        :param message: The message to log.
        :type message: str
        """
        chatbot_helper_logger.info("%s: %s", self.formatted_class_name, message)

    def helper_warning(self, message: str):
        """
        Create a log warning entry.

        This method writes an informational log entry using the
        :data:`chatbot_helper_logger`, including the formatted class name
        and the provided message.

        :param message: The message to log.
        :type message: str
        """
        logger.warning("%s: %s", self.formatted_class_name, message)

    def log_dump(self):
        """
        Dumps the ChatBotHelper state to the helper logger.
        This method serializes the current state of the ChatBotHelper
        instance to JSON format and logs it using the helper logger.
        It includes horizontal lines for better readability in the logs.

        :returns: None if the ChatBot is not initialized or logging is disabled.
        :rtype: None
        """
        if not self._chatbot and waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_HELPER_LOGGING):
            return None

        horizontal_line = "-" * (80 - 15)
        self.helper_logger(horizontal_line)
        self.helper_logger(json.dumps(self.to_json()))
        self.helper_logger(horizontal_line)


def get_cached_chatbot_by_request(request: HttpRequest) -> Optional[ChatBot]:
    """
    Returns the chatbot from the cache if it exists, otherwise
    it queries the database with assistance from ChatBotHelper
    and caches the result.
    """
    url = smarter_build_absolute_uri(request)
    if not url:
        return None
    url = clean_url(url)

    def get_chatbot_by_url(url: str) -> Optional[ChatBot]:
        chatbot_helper = ChatBotHelper(request)
        if chatbot_helper.is_valid:
            chatbot = chatbot_helper.chatbot
            if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                logging.info("get_cached_chatbot_by_request() caching chatbot %s for %s", chatbot, url)
            return chatbot

    return get_chatbot_by_url(url)
