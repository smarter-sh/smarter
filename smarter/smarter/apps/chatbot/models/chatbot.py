# pylint: disable=W0613,C0115,C0302
"""All models for the OpenAI Function Calling API app."""

import warnings
from typing import Optional
from urllib.parse import urljoin, urlparse

from django.core.exceptions import ValidationError
from django.db import models

from smarter.apps.account.models import (
    Account,
    MetaDataWithOwnershipModel,
    User,
    UserProfile,
)
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
)
from smarter.apps.chatbot.signals import (
    chatbot_deploy,
    chatbot_deploy_failed,
    chatbot_deploy_status_changed,
    chatbot_dns_failed,
    chatbot_dns_verification_initiated,
    chatbot_dns_verification_status_changed,
    chatbot_dns_verified,
    chatbot_undeploy,
)
from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import (
    formatted_text,
)
from smarter.common.helpers.llm import get_date_time_string
from smarter.common.utils import rfc1034_compliant_str
from smarter.lib import json, logging
from smarter.lib.cache import cache_results
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

from .chatbot_custom_domain import ChatBotCustomDomain
from .chatbot_custom_domain_dns import ChatBotCustomDomainDNS

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.CHATBOT_LOGGING])


def validate_provider(value):
    """
    Validate that the provider is in the list of valid chat providers.

    :param value: The provider value to validate.
    :raises ValidationError: If the provider is not valid.

    :returns: None
    """
    # pylint: disable=C0415
    from smarter.apps.provider.services.text_completion.providers import (
        smarter_compatible_client,
    )

    if not value in smarter_compatible_client.all:
        raise ValidationError(
            "%(value)s is not a valid provider. Valid providers are: %(providers)s",
            params={"value": value, "providers": str(smarter_compatible_client.all)},
        )


class ChatBot(MetaDataWithOwnershipModel):
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
        unique_together = ("user_profile", "name")

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

    # objects: MetaDataWithOwnershipModelManager["ChatBot"] = MetaDataWithOwnershipModelManager()

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
    app_example_prompts = models.JSONField(
        default=list,
        blank=True,
        null=True,
        encoder=json.SmarterJSONEncoder,
    )

    #: The ChatBot UI configuration fields. Placeholder text in the chat input area.
    #: Example: "Ask me anything about Stackademy..."
    app_placeholder = models.CharField(default="Type something here...", max_length=255, blank=True, null=True)

    #: The ChatBot UI configuration fields. URL to the app information button in the top-right
    #: of the Smarter React ChatBot component.
    #: Example: "https://smarter.sh"
    app_info_url = models.URLField(default="https://smarter.sh", blank=True, null=True)

    #: The ChatBot UI configuration fields. URL to the app background image in the Smarter React ChatBot component.
    #: Example: "https://cdn.smarter.sh/chat-ui/background.png"
    app_background_image_url = models.URLField(blank=True, null=True)

    #: The ChatBot UI configuration fields. URL to the app logo image in the Smarter React ChatBot component.
    #: Example: "https://cdn.smarter.sh/chat-ui/logo.png"
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
        Returns a RFC 1034 compliant name for the ChatBot. This name is used
        in the hostname of the ChatBot's default and custom URLs. The name
        is constructed by combining the ChatBot's name and the username of
        the associated user profile, separated by a dot. The resulting name
        adheres to the following rules:

        - lower case
        - alphanumeric characters and hyphens only [a-z0-9-]
        - starts and ends with an alphanumeric character
        - max length of 63 characters
        - no consecutive hyphens
        - no leading or trailing hyphens
        - no underscores or special characters
        - no spaces
        - no dots except for separating the ChatBot name and username
        - no more than one dot

        Examples:

        - For a ChatBot with name "example" and associated user profile "adminuser",
            that IS the account admin, the resulting RFC 1034 compliant name
            would be "example"

        - For a ChatBot with name "example" and associated user profile "user123",
            that is NOT the account admin, the resulting RFC 1034 compliant name
            would be "example.user123"

        :returns: RFC 1034 compliant name
        :rtype: str
        """
        user_profile: UserProfile = self.user_profile
        admin_user = get_cached_admin_user_for_account(account=user_profile.cached_account)  # type: ignore[arg-type]
        if user_profile.cached_user == admin_user:
            raw_str = self.name
        else:
            # note: rfc1034_compliant_str() filters out the "."
            raw_str = f"{self.name}-{user_profile.user.username}"
        return rfc1034_compliant_str(raw_str)

    @property
    def default_system_role_enhanced(self):
        """
        prepends a date/time string to the default_system_role

        Example: "2024-06-01 12:00:00 System: You are a helpful assistant."
        :returns: enhanced system role string
        :rtype: str
        """
        return f"{get_date_time_string()}{self.default_system_role}"

    @property
    def base_api_domain(self):
        """
        The base API domain for the ChatBot. This is the domain that is used in the default hostname for the ChatBot.

        Examples:

            example 1. given:

            - environment is "alpha"
            - environment API domain "alpha.api.example.com"

            the resulting base API domain would be: 'alpha.api.example.com'

            example 2. given:

            - environment is "local"
            - environment API domain "api.localhost:9357"

            the resulting base API domain would be: 'api.local.example.com'

        """
        if smarter_settings.environment in SmarterEnvironments.aws_environments:
            return smarter_settings.environment_api_domain
        return smarter_settings.proxy_api_domain

    @property
    def base_default_host(self):
        """
        The base default hostname for the ChatBot. This is the part of the hostname
        that comes after the RFC 1034 compliant name. It includes the account number
        and the environment API domain.

        Examples:

            example 1. given:

            - a ChatBot associated with an account number "1234-5678-9012"
            - environment is "alpha"
            - environment API domain "alpha.api.example.com"

            the resulting base default host would be: '.1234-5678-9012.alpha.api.example.com'

            example 2. given:

            - a ChatBot associated with an account number "1234-5678-9012"
            - environment is "local"
            - environment API domain "api.localhost:9357"

            the resulting base default host would be: '.1234-5678-9012.api.local.example.com'

        """
        user_profile: UserProfile = self.user_profile
        return f"{user_profile.account.account_number}.{self.base_api_domain}"

    @property
    def default_host(self):
        """
        The default hostname for the ChatBot.
        Examples:

        example 1. given:

        - self.name: 'example'
        - self.account.account_number: '1234-5678-9012'
        - smarter_settings.environment = "alpha"
        - smarter_settings.environment_api_domain: 'alpha.api.example.com'

        The domain would be: 'example.1234-5678-9012.alpha.api.example.com'

        example 2. given:

        - self.name: 'example'
        - self.account.account_number: '1234-5678-9012'
        - smarter_settings.environment = "local"
        - smarter_settings.environment_api_domain: 'api.localhost:9357'

        The domain would be: 'example.1234-5678-9012.api.local.example.com'

        :returns: default hostname
        :rtype: str
        """
        domain = f"{self.rfc1034_compliant_name}.{self.base_default_host}"
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

        example: 'https://alpha.platform.smarter.sh/workbench/chatbots/<str:hashed_id>/'

        :returns: sandbox URL
        :rtype: str
        """
        # pylint: disable=C0415
        from smarter.apps.prompt.urls import PromptReverseNames

        path = reverse(f"{PromptReverseNames.namespace}:{PromptReverseNames.landing_by_hashed_id}", kwargs={"hashed_id": self.hashed_id})  # type: ignore[arg-type]
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
        example: "http://localhost:9357/api/v1/chatbots/5174/chat/"

        :returns: URL for chatbot API
        :rtype: str
        """
        # pylint: disable=C0415
        from smarter.apps.chatbot.api.v1.urls import ChatBotApiV1ReverseViews

        path = reverse(
            f"{ChatBotApiV1ReverseViews.namespace}:{ChatBotApiV1ReverseViews.default_chatbot_api_view_by_hashed_id}",
            kwargs={"hashed_id": self.hashed_id},
        )

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
        example: "http://localhost:9357/api/v1/chatbots/5174/config/"

        :returns: URL for chatbot config API
        :rtype: str
        """
        # pylint: disable=C0415
        from smarter.apps.chatbot.api.v1.urls import ChatBotApiV1ReverseViews

        path = reverse(
            f"{ChatBotApiV1ReverseViews.namespace}:{ChatBotApiV1ReverseViews.chat_config_view_by_hashed_id}",
            kwargs={"hashed_id": self.hashed_id},
        )
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
        # pylint: disable=C0415
        from smarter.apps.prompt.urls import PromptReverseNames

        path = reverse(f"{PromptReverseNames.namespace}:{PromptReverseNames.chat_by_hashed_id}", kwargs={"hashed_id": self.hashed_id})  # type: ignore[arg-type]
        url = urljoin(smarter_settings.environment_url, path)
        url = SmarterValidator.urlify(url, environment=smarter_settings.environment)  # type: ignore[return-value]
        return url

    @property
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

    @classmethod
    def get_cached_object(
        cls,
        *args,
        invalidate: Optional[bool] = False,
        pk: Optional[int] = None,
        name: Optional[str] = None,
        user: Optional[User] = None,
        user_profile: Optional[UserProfile] = None,
        account: Optional[Account] = None,
        **kwargs,
    ) -> "ChatBot":
        """
        Retrieve a model instance using caching to optimize performance.

        Example usage:

        .. code-block:: python

            # Retrieve a ChatBot instance by primary key with caching
            chatbot = ChatBot.get_cached_object(pk=1)

            # Retrieve a ChatBot instance by name and user profile with caching
            chatbot = ChatBot.get_cached_object(name="example", user_profile=my_user_profile)


        :param pk: The primary key of the model instance to retrieve.
        :param name: The name of the model instance to retrieve.
        :param user: The user associated with the model instance.
        :param user_profile: The user profile associated with the model instance.
        :param account: The account associated with the model instance.

        :returns: The model instance if found, otherwise None.
        :rtype: Optional["ChatBot"]
        """
        logger_prefix = formatted_text(__name__ + "." + ChatBot.__name__ + ".get_cached_object()")
        logger.debug(
            "%s called %s with pk=%s, name=%s, user=%s, user_profile=%s, account=%s, invalidate=%s",
            logger_prefix,
            cls.__name__,
            pk,
            name,
            user,
            user_profile,
            account,
            invalidate,
        )

        retval = super().get_cached_object(*args, invalidate=invalidate, pk=pk, name=name, user=user, user_profile=user_profile, account=account, **kwargs)  # type: ignore[assignment]
        if retval is None:
            raise ChatBot.DoesNotExist(f"{cls.__name__} matching query does not exist.")
        return retval  # type: ignore[return-value]

    @classmethod
    def get_cached_objects(
        cls, invalidate: Optional[bool] = False, user_profile: Optional[UserProfile] = None
    ) -> models.QuerySet["ChatBot"]:
        """
        Retrieve a list of ChatBot instances associated with a user profile using caching.

        Example usage:

        .. code-block:: python

            # Retrieve ChatBot instances for a user profile with caching
            chatbots = ChatBot.get_cached_objects(my_user_profile, invalidate=True)


        :param invalidate: Whether to invalidate the cache for this retrieval.
        :param user_profile: The user profile for which to retrieve ChatBot instances.

        :returns: A queryset of ChatBot instances associated with the user profile.
        :rtype: models.QuerySet["ChatBot"]

        """
        logger_prefix = formatted_text(__name__ + "." + ChatBot.__name__ + ".get_cached_objects()")
        logger.debug("%s called with user_profile=%s, invalidate=%s", logger_prefix, user_profile, invalidate)

        @cache_results()
        def _get_chatbots_for_user_profile_id(
            user_profile_id: int, class_name: str = cls.__name__
        ) -> models.QuerySet["ChatBot"]:
            return (
                cls.objects.with_read_permission_for(user=user_profile.user)  # type: ignore
                .prefetch_related("tags")
                .select_related("user_profile", "user_profile__account", "user_profile__user")
            )

        if invalidate and user_profile:
            _get_chatbots_for_user_profile_id.invalidate(user_profile_id=user_profile.id, class_name=cls.__name__)  # type: ignore[union-attr]

        if user_profile:
            return _get_chatbots_for_user_profile_id(user_profile_id=user_profile.id, class_name=cls.__name__)  # type: ignore[return-value]

        return super().get_cached_objects(user_profile=user_profile, invalidate=invalidate)  # type: ignore[return-value]

    def save(self, *args, asynchronous=False, **kwargs):
        """
        Override save() to validate domain and send signals on status changes.

        :raises SmarterValueError: If invalid hostname is provided.

        :args: Positional arguments for the save method.
        :asynchronous: If True, skips signal sending for asynchronous operations.
        :kwargs: Keyword arguments for the save method.
        :returns: None
        """
        logger.debug("%s.save() called for ChatBot id: %s %s", self.formatted_class_name, self.pk, self.default_host)
        if asynchronous:
            logger.debug(
                "%s.save() running in asynchronous mode for ChatBot id: %s. Skipping signal sending.",
                self.formatted_class_name,
                self.pk,
            )
            super().save(*args, **kwargs)
            return
        is_new = self.pk is None
        SmarterValidator.validate_domain(self.hostname)
        should_deploy = False
        should_undeploy = False
        if is_new:
            if self.deployed:
                chatbot_deploy.send(sender=self.__class__, chatbot=self)
        else:
            orig: ChatBot
            try:
                orig = ChatBot.objects.get(id=self.pk)
            except ChatBot.DoesNotExist:
                logger.error(
                    "%s.save() could not find original ChatBot with id: %s", self.formatted_class_name, self.pk
                )
                return super().save(*args, **kwargs)

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
                should_deploy = True
            if not self.deployed and orig.deployed:
                should_undeploy = True
        super().save(*args, **kwargs)
        if should_deploy:
            logger.debug(
                "%s.ChatBot.save() sending chatbot_deploy signal for ChatBot id: %s", self.formatted_class_name, self.pk
            )
            chatbot_deploy.send(sender=self.__class__, chatbot=self)
        if should_undeploy:
            logger.debug(
                "%s.ChatBot.save() sending chatbot_undeploy signal for ChatBot id: %s",
                self.formatted_class_name,
                self.pk,
            )
            chatbot_undeploy.send(sender=self.__class__, chatbot=self)


__all__ = ["ChatBot"]
