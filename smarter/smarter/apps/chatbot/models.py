# pylint: disable=W0613,C0115
"""All models for the OpenAI Function Calling API app."""
import json
import logging
from functools import cached_property
from typing import List, Type
from urllib.parse import urljoin

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.handlers.wsgi import WSGIRequest
from django.db import models
from rest_framework import serializers

# our stuff
from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.serializers import AccountMiniSerializer
from smarter.apps.account.utils import get_cached_user_profile
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.plugin.static import StaticPlugin
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_DEFAULT_CACHE_TIMEOUT
from smarter.common.helpers.llm import get_date_time_string
from smarter.common.helpers.url_helpers import clean_url
from smarter.common.utils import smarter_build_absolute_uri
from smarter.lib.cache import cache_results
from smarter.lib.django import waffle
from smarter.lib.django.model_helpers import TimestampedModel
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.models import SmarterAuthToken

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

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# ChatBot Models. These implement a ChatBot API for a customer account.
# -----------------------------------------------------------------------------
class ChatBotCustomDomain(TimestampedModel):
    """A ChatBot DNS Host for a customer account. Linked to an AWS Hosted Zone."""

    class Meta:
        verbose_name_plural = "ChatBot Custom Domains"

    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    aws_hosted_zone_id = models.CharField(max_length=255)
    domain_name = models.CharField(max_length=255)
    is_verified = models.BooleanField(default=False, blank=True, null=True)

    @classmethod
    def get_verified_domains(cls):
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
        if self.domain_name:
            SmarterValidator.validate_domain(self.domain_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.domain_name) if self.domain_name else "undefined"


class ChatBotCustomDomainDNS(TimestampedModel):
    """ChatBot DNS Records for a ChatBot DNS Host."""

    class Meta:
        verbose_name_plural = "ChatBot Custom Domain DNS"

    custom_domain = models.ForeignKey(ChatBotCustomDomain, on_delete=models.CASCADE)
    record_name = models.CharField(max_length=255)
    record_type = models.CharField(max_length=255)
    record_value = models.CharField(max_length=255)
    record_ttl = models.IntegerField(default=600, blank=True, null=True)


def validate_provider(value):
    # pylint: disable=C0415
    from smarter.apps.prompt.providers.providers import chat_providers

    if not value in chat_providers.all:
        raise ValidationError(
            "%(value)s is not a valid provider. Valid providers are: %(providers)s",
            params={"value": value, "providers": str(chat_providers.all)},
        )


class ChatBot(TimestampedModel):
    """A ChatBot API for a customer account."""

    class Meta:
        verbose_name_plural = "ChatBots"
        unique_together = ("account", "name")

    class Modes:
        """ChatBot API Modes"""

        SANDBOX = "sandbox"
        CUSTOM = "custom"
        DEFAULT = "default"
        UNKNOWN = "unknown"

    class Schemes:
        """ChatBot API Schemes"""

        HTTP = "http"
        HTTPS = "https"

    class DnsVerificationStatusChoices(models.TextChoices):
        VERIFYING = "Verifying", "Verifying"
        NOT_VERIFIED = "Not Verified", "Not Verified"
        VERIFIED = "Verified", "Verified"
        FAILED = "Failed", "Failed"

    class TlsCertificateIssuanceStatusChoices(models.TextChoices):
        NO_CERTIFICATE = "No Certificate", "No Certificate"
        REQUESTED = "Requested", "Requested"
        ISSUED = "Issued", "Issued"
        FAILED = "Failed", "Failed"

    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    version = models.CharField(max_length=255, blank=True, null=True)
    subdomain = models.ForeignKey(ChatBotCustomDomainDNS, on_delete=models.CASCADE, blank=True, null=True)
    custom_domain = models.ForeignKey(ChatBotCustomDomain, on_delete=models.CASCADE, blank=True, null=True)
    deployed = models.BooleanField(default=False, blank=True, null=True)
    provider = models.CharField(
        default=smarter_settings.llm_default_provider,
        max_length=255,
        blank=True,
        null=True,
        validators=[validate_provider],
    )
    default_model = models.CharField(max_length=255, blank=True, null=True)
    default_system_role = models.TextField(default=smarter_settings.llm_default_system_role, blank=True, null=True)
    default_temperature = models.FloatField(default=smarter_settings.llm_default_temperature, blank=True, null=True)
    default_max_tokens = models.IntegerField(default=smarter_settings.llm_default_max_tokens, blank=True, null=True)

    app_name = models.CharField(default="chatbot", max_length=255, blank=True, null=True)
    app_assistant = models.CharField(default="Smarter", max_length=255, blank=True, null=True)
    app_welcome_message = models.CharField(default="Welcome to the chatbot!", max_length=255, blank=True, null=True)
    app_example_prompts = models.JSONField(default=list, blank=True, null=True)
    app_placeholder = models.CharField(default="Type something here...", max_length=255, blank=True, null=True)
    app_info_url = models.URLField(default="https://smarter.sh", blank=True, null=True)
    app_background_image_url = models.URLField(blank=True, null=True)
    app_logo_url = models.URLField(blank=True, null=True)
    app_file_attachment = models.BooleanField(default=False, blank=True, null=True)
    dns_verification_status = models.CharField(
        max_length=255,
        default=DnsVerificationStatusChoices.NOT_VERIFIED,
        blank=True,
        null=True,
        choices=DnsVerificationStatusChoices.choices,
    )
    tls_certificate_issuance_status = models.CharField(
        max_length=255,
        default=TlsCertificateIssuanceStatusChoices.NO_CERTIFICATE,
        blank=True,
        null=True,
        choices=TlsCertificateIssuanceStatusChoices.choices,
    )

    @property
    def default_system_role_enhanced(self):
        """
        prepends a date/time string to the default_system_role
        """
        return f"{get_date_time_string()}{self.default_system_role}"

    @property
    def default_host(self):
        """
        self.name: 'example'
        self.account.account_number: '1234-5678-9012'
        smarter_settings.environment_api_domain: 'alpha.api.smarter.sh'
        """
        domain = f"{self.name}.{self.account.account_number}.{smarter_settings.environment_api_domain}"
        SmarterValidator.validate_domain(domain)
        return domain

    @property
    def default_url(self):
        return SmarterValidator.urlify(self.default_host, environment=smarter_settings.environment)

    @property
    def custom_host(self):
        """
        self.name: 'example'
        self.custom_domain.domain_name: 'example.com'
        """
        if self.custom_domain and self.custom_domain.is_verified:
            domain = f"{self.name}.{self.custom_domain.domain_name}"
            SmarterValidator.validate_domain(domain)
            return domain
        return None

    @property
    def custom_url(self):
        """
        return 'https://example.example.com'
        """
        if self.custom_host:
            return SmarterValidator.urlify(self.custom_host, environment=smarter_settings.environment)
        return None

    @property
    def sandbox_host(self):
        """
        return 'alpha.api.smarter.sh/api/v1/chatbots/1/'
        """
        domain = f"{smarter_settings.environment_domain}/api/v1/chatbots/{self.id}/"
        SmarterValidator.validate_domain(domain)
        return domain

    @property
    def sandbox_url(self):
        """
        return 'https://alpha.api.smarter.sh/api/v1/chatbots/1/'
        """
        return SmarterValidator.urlify(self.sandbox_host, environment=smarter_settings.environment)

    @property
    def hostname(self):
        if self.deployed:
            return self.custom_host or self.default_host
        return self.sandbox_host

    @property
    def scheme(self):
        return ChatBot.Schemes.HTTP if smarter_settings.environment == "local" else ChatBot.Schemes.HTTPS

    @property
    def url(self):
        if self.deployed:
            return self.custom_url or self.default_url
        return self.sandbox_url

    @property
    def url_chatbot(self):
        """
        returned by ChatConfigView.config()
        consumed by React.js app for http requests on new prompts
        interpreted by smarter.apps.chatbot.api.v1.urls.py as
        path("<int:chatbot_id>/chat/", ChatConfigView.as_view(), name="chatbot-api-chatbot")
        """
        base_url = smarter_settings.environment_domain
        return urljoin(self.scheme + "://" + base_url, f"/api/v1/chatbots/{self.id}/chat/")

    @property
    def url_chatapp(self):
        return urljoin(self.url, "chatapp/")

    def ready(self):
        """
        A ChatBot is ready if it is its in sandbox mode, or, if it is:
        - deployed
        - has a verified DNS A record
        - has a valid, issued tls certificate.
        """
        if self.mode(self.url) == self.Modes.SANDBOX:
            return True

        return (
            self.dns_verification_status == self.DnsVerificationStatusChoices.VERIFIED
            and self.deployed
            and self.tls_certificate_issuance_status == self.TlsCertificateIssuanceStatusChoices.ISSUED
        )

    def mode(self, url: str) -> str:
        logger.debug("mode: %s", url)
        if not url:
            return self.Modes.UNKNOWN
        SmarterValidator.validate_url(url)
        url = SmarterValidator.urlify(url, environment=smarter_settings.environment)
        custom_url = SmarterValidator.urlify(self.custom_host, environment=smarter_settings.environment)
        default_url = SmarterValidator.urlify(self.default_host, environment=smarter_settings.environment)
        sandbox_url = SmarterValidator.urlify(self.sandbox_host, environment=smarter_settings.environment)
        if custom_url and custom_url in url:
            return self.Modes.CUSTOM
        if default_url and default_url in url:
            return self.Modes.DEFAULT
        if sandbox_url and sandbox_url in url:
            return self.Modes.SANDBOX
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

    def __str__(self):
        return self.url if self.url else "undefined"


class ChatBotAPIKey(TimestampedModel):
    """Map of API keys for a ChatBot"""

    class Meta:
        verbose_name_plural = "ChatBot API Keys"

    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE)
    api_key = models.ForeignKey(SmarterAuthToken, on_delete=models.CASCADE)


class ChatBotPlugin(TimestampedModel):
    """List of Plugins for a ChatBot"""

    class Meta:
        verbose_name_plural = "ChatBot Plugins"
        unique_together = ("chatbot", "plugin_meta")

    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE)
    plugin_meta = models.ForeignKey(PluginMeta, on_delete=models.CASCADE)

    def __str__(self):
        return f"{str(self.chatbot.url)} - {str(self.plugin_meta.name)}"

    @property
    def plugin(self) -> StaticPlugin:
        if not self.chatbot:
            return None
        admin_user = UserProfile.admin_for_account(self.chatbot.account)
        user_profile = get_cached_user_profile(admin_user)
        return StaticPlugin(plugin_meta=self.plugin_meta, user_profile=user_profile)

    @classmethod
    def load(cls: Type["ChatBotPlugin"], chatbot: ChatBot, data) -> "ChatBotPlugin":
        """Load (aka import) a plugin from a data file in yaml or json format."""
        if not chatbot:
            return None
        admin_user = UserProfile.admin_for_account(chatbot.account)
        user_profile = get_cached_user_profile(admin_user)
        plugin = StaticPlugin(data=data, user_profile=user_profile)
        return cls.objects.create(chatbot=chatbot, plugin_meta=plugin.meta)

    @classmethod
    def plugins(cls, chatbot: ChatBot) -> List[StaticPlugin]:
        if not chatbot:
            return []
        chatbot_plugins = cls.objects.filter(chatbot=chatbot)
        admin_user = UserProfile.admin_for_account(chatbot.account)
        user_profile = get_cached_user_profile(admin_user)
        retval = []
        for chatbot_plugin in chatbot_plugins:
            retval.append(StaticPlugin(plugin_meta=chatbot_plugin.plugin_meta, user_profile=user_profile))
        return retval

    @classmethod
    def plugins_json(cls, chatbot: ChatBot) -> List[dict]:
        retval = []
        for plugin in cls.plugins(chatbot):
            retval.append(plugin.to_json())
        return retval


class ChatBotFunctions(TimestampedModel):
    """List of Functions for a ChatBot"""

    class Meta:
        verbose_name_plural = "ChatBot Functions"

    CHOICES = [
        ("weather", "weather"),
        ("news", "news"),
        ("prices", "prices"),
        ("math", "math"),
    ]

    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, choices=CHOICES, blank=True, null=True)

    @classmethod
    def choices_list(cls):
        return [item[0] for item in cls.CHOICES]


class ChatBotRequests(TimestampedModel):
    """List of Requests for a ChatBot"""

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
def get_cached_chatbot(chatbot_id: int = None, name: str = None, account: Account = None) -> ChatBot:
    """
    Returns the chatbot from the cache if it exists, otherwise
    it queries the database and caches the result.
    """
    chatbot: ChatBot = None

    if chatbot_id:
        chatbot = ChatBot.objects.get(id=chatbot_id)
    else:
        if name and account:
            chatbot = ChatBot.objects.get(name=name, account=account)

    return chatbot


class ChatBotHelper(SmarterRequestMixin):
    """Maps urls and attribute data to their respective ChatBot models.
    Abstracts url parsing logic so that we can use it in multiple
    places: inside this module, in middleware, in Views, etc.

    Also caches the ChatBot object for a given url so that we don't have to
    parse the url multiple times.

    examples of valid urls:
    # authentication optional urls
    - https://example.3141-5926-5359.alpha.api.smarter.sh/
    - https://example.3141-5926-5359.alpha.api.smarter.sh/config/

    # authenticated urls
    - https://alpha.api.smarter.sh/smarter/example/
    - https://example.smarter.querium.com/chatbot/
    - https://alpha.api.smarter.sh/workbench/1/
    - https://alpha.api.smarter.sh/workbench/example/

    # legacy pre v0.12 urls
    - https://alpha.api.smarter.sh/chatbots/1/
    - https://alpha.api.smarter.sh/chatbots/example/

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
        Returns the formatted class name for the ChatBotHelper.
        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.ChatBotHelper()"

    def __init__(self, request: WSGIRequest, *args, **kwargs):
        """
        Constructor for ChatBotHelper.
        :param url: The URL to parse.
        :param environment: The environment to use for the URL. (for unit testing only)
        """
        self._chatbot: ChatBot = None
        self._chatbot_custom_domain: ChatBotCustomDomain = None
        self._chatbot_requests: ChatBotRequests = None
        self._chatbot_id: int = None
        self._name: str = None
        self._err: str = None

        super().__init__(request, **kwargs)

        name: str = kwargs.get("name")
        chatbot_id: int = kwargs.get("chatbot_id")

        self._chatbot_id: int = self._chatbot_id or chatbot_id or self.smarter_request_chatbot_id
        self._name: str = self._name or name or self.smarter_request_chatbot_name

        if waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_HELPER_LOGGING):
            logger.info(
                "%s.__init__() initialized with url=%s, name=%s, chatbot_id=%s, user=%s, account=%s, session_key=%s",
                self.formatted_class_name,
                self.url,
                self.name,
                self.chatbot_id,
                self.user,
                self.account,
                self.session_key,
            )

        if self.ready:
            self.helper_logger(f"__init__() initialized self.chatbot={self.chatbot}")
            return None

        if waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_HELPER_LOGGING):
            self.helper_logger(
                f"__init__() url={ self.url } name={ self.name } chatbot_id={ self.chatbot_id } user={ self.user } account={ self.account }."
            )

        self._chatbot = self._chatbot or get_cached_chatbot(account=self.account, name=self.name)
        if self.ready:
            self.helper_logger(f"__init__() initialized self.chatbot={self.chatbot} from account and name")
            return None

        self.helper_warning(
            f"__init__() failed to initialize self.chatbot with url={ self.url } name={ self.name } chatbot_id={ self.chatbot_id } user={ self.user } account={ self.account }."
        )

    def __str__(self):
        return str(self.chatbot) if self._chatbot else "undefined"

    @property
    def chatbot_id(self) -> int:
        """
        Returns the ChatBot.id for the ChatBotHelper.
        """
        # check for a value passed in
        if self._chatbot_id:
            return self._chatbot_id

        # check for a chatbot object
        if self._chatbot:
            self._chatbot_id = self.chatbot.id
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
            raise ValueError("ChatBotHelper.chatbot_id setter: chatbot.account does not match self.account")
        self._chatbot = chatbot
        if self._chatbot:
            self.helper_logger(f"@chatbot_id.setter initialized self.chatbot_id={self.chatbot_id} from chatbot_id")

    @property
    def chatbot_name(self) -> str:
        """
        Returns the ChatBot.name for the ChatBotHelper.
        """
        return self.name

    @property
    def name(self):
        """
        Returns the name of the chatbot.
        valid possibilities:
        - self._name, assigned in __init__()
        - self.chatbot.name
        - self.subdomain when is_chatbot_named_url
        - self.path slug when is_chatbot_sandbox_url
        """
        if self._chatbot:
            self._name = self.chatbot.name

        if self._name:
            return self._name

        self._name = super().smarter_request_chatbot_name

        if not self._name and self.is_chatbot_named_url:
            # covers a case like http://example.api.localhost:8000/
            self._name = self.parsed_url.hostname.split(".")[0]

        if not self._name and self.is_chatbot_sandbox_url:
            # covers a case like http://localhost:8000/workbench/example/
            path_parts = self.parsed_url.path.split("/")
            if len(path_parts) > 2:
                self._name = path_parts[2]

        return self._name

    @property
    def ready(self) -> bool:
        return super().ready and self._chatbot

    def to_json(self):
        """
        Serialize the ChatBotHelper.
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
    def api_host(self) -> str:
        """
        Returns the API host for a ChatBot API url.
        :return: The API host or None if not found.

        named url:
        - https://hr.3141-5926-5359.alpha.api.smarter.sh/chatbot/
          returns 'alpha.api.smarter.sh'

        sandbox url:
        - http://api.localhost:8000/api/v1/chatbots/1/chat/
          return 'api.localhost:8000'

        custom domain url:
        - https://hr.smarter.querium.com/chatbot/
          return 'hr.smarter.querium.com'

        """
        if self.is_smarter_api:
            return self._url.netloc
        if self.is_custom_domain:
            # example: hr.bots.example.com
            return self._url.netloc
        return smarter_settings.environment_api_domain

    @property
    def is_deployed(self) -> bool:
        return self.chatbot.deployed if self.chatbot else False

    @property
    def is_valid(self) -> bool:
        """
        Validates whether the ChatBot is in a ready state,
        and if it is usable for making API calls.
        """
        if not self.ready:
            self._err = f"is_valid() returning false because ChatBotHelper is not in a ready state: {self.url}"
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
        if self.is_chatbot_sandbox_url:
            return True

        if ChatBotAPIKey.objects.filter(chatbot=self.chatbot, api_key__is_active=True).exists():
            return True
        return False

    @property
    def chatbot(self) -> ChatBot:
        """
        Returns a lazy instance of the ChatBot
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
        return self._chatbot_custom_domain is not None

    @property
    def chatbot_custom_domain(self) -> ChatBotCustomDomain:
        """
        Returns a lazy instance of the ChatBotCustomDomain

        examples:
        - https://hr.smarter.querium.com/chatbot/
          returns ChatBotCustomDomain(domain_name='smarter.querium.com')
        """
        if self._chatbot_custom_domain:
            return self._chatbot_custom_domain

        if not self.url:
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
        Create a log entry
        """
        if waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_HELPER_LOGGING):
            logger.info("%s: %s", self.formatted_class_name, message)

    def helper_warning(self, message: str):
        """
        Create a log entry
        """
        logger.warning("%s: %s", self.formatted_class_name, message)

    def log_dump(self):
        if not self._chatbot and waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_HELPER_LOGGING):
            return None

        horizontal_line = "-" * (80 - 15)
        self.helper_logger(horizontal_line)
        self.helper_logger(json.dumps(self.to_json(), indent=4))
        self.helper_logger(horizontal_line)


def get_cached_chatbot_by_request(request: WSGIRequest) -> ChatBot:
    """
    Returns the chatbot from the cache if it exists, otherwise
    it queries the database with assistance from ChatBotHelper
    and caches the result.
    """
    url = smarter_build_absolute_uri(request)
    if not url:
        return None
    url = clean_url(url)

    @cache_results()
    def get_chatbot_by_url(url: str) -> ChatBot:
        chatbot_helper = ChatBotHelper(request=request)
        if chatbot_helper.is_valid:
            chatbot = chatbot_helper.chatbot
            logging.info("get_cached_chatbot_by_request() caching chatbot %s for %s", chatbot, url)
            return chatbot

    return get_chatbot_by_url(url)
