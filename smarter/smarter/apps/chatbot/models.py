# pylint: disable=W0613,C0115
"""All models for the OpenAI Function Calling API app."""
import logging
import re
from typing import List, Type
from urllib.parse import ParseResult, urljoin, urlparse

import tldextract
import waffle
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models
from rest_framework import serializers

from smarter.apps.account.mixins import AccountMixin

# our stuff
from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.serializers import AccountMiniSerializer
from smarter.apps.account.utils import (
    SMARTER_ACCOUNT_NUMBER_REGEX,
    account_number_from_url,
    smarter_admin_user_profile,
    user_profile_for_user,
)
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.plugin.static import PluginStatic
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SmarterWaffleSwitches
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django.model_helpers import TimestampedModel
from smarter.lib.django.user import UserType
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.drf.models import SmarterAuthToken

from .signals import (
    chatbot_dns_failed,
    chatbot_dns_verification_initiated,
    chatbot_dns_verification_status_changed,
    chatbot_dns_verified,
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
        cache_expiration = 5 * 60  # 5 minutes
        cache_key = "ChatBotCustomDomain_chatbot_verified_custom_domains"
        verified_domains = cache.get(cache_key)

        # If the list is not in cache, fetch it from the database
        if not verified_domains:
            verified_domains = list(cls.objects.filter(is_verified=True).values_list("domain_name", flat=True))
            cache.set(key=cache_key, value=verified_domains, timeout=cache_expiration)

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
    from smarter.apps.chat.providers.providers import chat_providers

    if not value in chat_providers.all:
        raise ValidationError(
            "%(value)s is not a valid provider. Valid providers are: %(providers)s",
            params={"value": value, "providers": str(chat_providers.all)},
        )


class ChatBot(TimestampedModel):
    """A ChatBot API for a customer account."""

    class Meta:
        verbose_name_plural = "ChatBots"

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

    @property
    def default_host(self):
        """
        self.name: 'example'
        self.account.account_number: '1234-5678-9012'
        smarter_settings.customer_api_domain: 'alpha.api.smarter.sh'
        """
        domain = f"{self.name}.{self.account.account_number}.{smarter_settings.customer_api_domain}"
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
        base_url = smarter_settings.environment_domain
        return urljoin(self.scheme + "://" + base_url, f"/api/v1/chatbots/{self.id}/")

    @property
    def url_chatapp(self):
        return urljoin(self.url, "chatapp/")

    @staticmethod
    def get_by_request(request):
        host = request.get_host()
        url = SmarterValidator.urlify(host, environment=smarter_settings.environment)
        parsed_host = urlparse(url)
        host = parsed_host.hostname
        return ChatBot.get_by_url(url)

    @staticmethod
    # @cache_results(timeout=600)
    def get_by_url(url: str):
        logger.debug("ChatBot() get_by_url: %s", url)
        url = SmarterValidator.urlify(url, environment=smarter_settings.environment)
        retval = ChatBotHelper(url).chatbot
        return retval

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
        logger.error("Invalid ChatBot url %s received for default_url: %s", url, self.default_url)
        logger.error("sandbox_url: %s", self.sandbox_url)
        logger.error("custom_url: %a", self.custom_url)
        # default to default mode as a safety measure
        return self.Modes.UNKNOWN

    def save(self, *args, **kwargs):
        SmarterValidator.validate_domain(self.hostname)
        orig = ChatBot.objects.get(pk=self.pk) if self.pk is not None else self
        super().save(*args, **kwargs)
        if self.pk is not None:
            if orig.dns_verification_status != self.dns_verification_status:
                chatbot_dns_verification_status_changed.send(sender=self.__class__, chatbot=self)
                if self.dns_verification_status == ChatBot.DnsVerificationStatusChoices.VERIFYING:
                    chatbot_dns_verification_initiated.send(sender=self.__class__, chatbot=self)
                if self.dns_verification_status == ChatBot.DnsVerificationStatusChoices.VERIFIED:
                    chatbot_dns_verified.send(sender=self.__class__, chatbot=self)
                if self.dns_verification_status == ChatBot.DnsVerificationStatusChoices.FAILED:
                    chatbot_dns_failed.send(sender=self.__class__, chatbot=self)

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
    def plugin(self) -> PluginStatic:
        if not self.chatbot:
            return None
        admin_user = UserProfile.admin_for_account(self.chatbot.account)
        user_profile = user_profile_for_user(admin_user)
        return PluginStatic(plugin_meta=self.plugin_meta, user_profile=user_profile)

    @classmethod
    def load(cls: Type["ChatBotPlugin"], chatbot: ChatBot, data) -> "ChatBotPlugin":
        """Load (aka import) a plugin from a data file in yaml or json format."""
        if not chatbot:
            return None
        admin_user = UserProfile.admin_for_account(chatbot.account)
        user_profile = user_profile_for_user(admin_user)
        plugin = PluginStatic(data=data, user_profile=user_profile)
        return cls.objects.create(chatbot=chatbot, plugin_meta=plugin.meta)

    @classmethod
    def plugins(cls, chatbot: ChatBot) -> List[PluginStatic]:
        if not chatbot:
            return []
        chatbot_plugins = cls.objects.filter(chatbot=chatbot)
        admin_user = UserProfile.admin_for_account(chatbot.account)
        user_profile = user_profile_for_user(admin_user)
        retval = []
        for chatbot_plugin in chatbot_plugins:
            retval.append(PluginStatic(plugin_meta=chatbot_plugin.plugin_meta, user_profile=user_profile))
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


class ChatBotHelper(AccountMixin):
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
    - https://alpha.api.smarter.sh/chatbots/1/
    - https://alpha.api.smarter.sh/chatbots/example/
    - https://alpha.api.smarter.sh/smarter/example/
    - https://example.smarter.querium.com/chatbot/
    """

    __slots__ = [
        "_chatbot",
        "_chatbot_custom_domain",
        "_chatbot_requests",
        "_chatbot_id",
        "_url",
        "_account_number",
        "_environment",
        "_name",
    ]

    def __init__(
        self,
        url: str = None,
        user: UserType = None,
        account: Account = None,
        name: str = None,
        environment: str = None,
        chatbot_id: int = None,
    ):
        """
        Constructor for ChatBotHelper.
        :param url: The URL to parse.
        :param environment: The environment to use for the URL. (for unit testing only)
        """
        self._chatbot: ChatBot = None
        self._chatbot_custom_domain: ChatBotCustomDomain = None
        self._chatbot_requests: ChatBotRequests = None

        self._chatbot_id: int = chatbot_id
        self._url: str = url
        self._account_number: str = account.account_number if account else None
        self._environment: str = environment
        self._name: str = name
        self.user: UserType = user

        # in a lot of cases this is as far as we'll need to go.
        if (self.url and self.url == smarter_settings.environment_url) or (
            self.parsed_url and self.parsed_url.path == "/"
        ):
            return None

        self._chatbot: ChatBot = self.get_from_cache()
        if self._chatbot:
            return None

        self.helper_logger(
            f"__init__() received: url={url}, user={user}, account={account}, name={name}, chatbot_id={chatbot_id}"
        )

        if not url and not name and not account and not chatbot_id:
            return None

        super().__init__(account=account, user=user, account_number=self.account_number)

        if chatbot_id:
            self._chatbot_id = chatbot_id
            self._chatbot = self.get_from_cache()
            if not self._chatbot:
                try:
                    chatbot = ChatBot.objects.get(id=chatbot_id)
                    self.set_to_cache(chatbot)
                    self._chatbot = chatbot
                    self._account = self.chatbot.account
                    self._name = self.chatbot.name
                except ChatBot.DoesNotExist as e:
                    raise SmarterValueError(f"ChatBot with id={chatbot_id} does not exist") from e
            return None

        if url:
            url = self.clean_url(url)  # eliminates url params and prunes trailing slugs like /config/
            SmarterValidator.validate_url(url)  # raises ValidationError if url is invalid
            url = SmarterValidator.urlify(
                url, environment=smarter_settings.environment
            )  # normalizes the url so that we dont find ourselves working with variations of the same url

            if url == smarter_settings.environment_url:
                self.helper_logger(f"nothing to do for self.url={url}")
                return None
            self._url = url

            self.helper_logger(f"__init__() initialized self.url={self.url} from url")

            # example: https://example.3141-5926-5359.api.smarter.sh
            if self.is_named_url:
                self._name = self.api_subdomain
                self.helper_logger(f"__init__() initialized self.name={self.name} from named url")
                self._account_number = account_number_from_url(self.url)
                self.helper_logger(f"__init__() initialized self.account_number={self.account_number} from named url")
                if self._account_number:
                    self._account = Account.objects.get(account_number=self.account_number)
                    self.helper_logger(f"__init__() initialized self.account={self.account} from account number")
                self._chatbot = self._chatbot or self.get_from_cache()
                if self._chatbot:
                    return None

                if self.name and self.account_number:
                    self._chatbot = ChatBot.objects.get(account=self.account, name=self.name)
                    self.set_to_cache(self._chatbot)
                    self.helper_logger(f"__init__() initialized self.chatbot={self.chatbot} from named url")
                    return None

        if self._chatbot:
            return None

        if name and not self._name:
            self._name = name
            self.helper_logger(f"__init__() initialized self.name={self.name} from name")

        if account and not self._account:
            self._account = account
            self.helper_logger(f"__init__() initialized self.account={self.account} from account")

        if user and not self._user:
            self._user = user
            self.helper_logger(f"__init__() initialized self.user={self.user} from user")

        if environment and not self._environment:
            self._environment = environment
            self.helper_logger(f"__init__() initialized self.environment={self.environment} from environment")

        if self.account:
            self._account_number = self.account.account_number

        # middleware sends lots of airballs to ChatBotHelper bc it doesn't
        # know how to distinguish between a ChatBot url Vs any other url.
        # therefore, we won't consider ourselves to be initializing unless
        # we make it past this point.
        self.helper_logger(
            f"__init__() interim evaluation chatbot={self.chatbot}, url={self.url}, name={self.name}, account={self.account}"
        )

        # 1. return a cached object if we have one.
        #    first, check to see if the cache key exists bc we also cache and return None values
        self._chatbot = self._chatbot or self.get_from_cache()
        if self._chatbot:
            return None

        self.helper_logger(f"__init__() cache miss. cache_key={self.cache_key}")

        # 2a. try using account and name
        if self.account and self.name:
            try:
                self._chatbot = ChatBot.objects.get(account=self.account, name=self.name)
                self.set_to_cache(self._chatbot)
                self.helper_logger(
                    f"__init__() initialized self.chatbot={self.chatbot} from account {self.account} and name {self.name}"
                )
                return None
            except ChatBot.DoesNotExist:
                # 2b. try again using the Smarter admin account in case this is a demo chatbot
                smarter_admin = smarter_admin_user_profile()
                try:
                    self._chatbot = ChatBot.objects.get(account=smarter_admin.account, name=self.name)
                except ChatBot.DoesNotExist:
                    self.helper_warning(f"did not find chatbot using {self.account} and {self.name}")

        if self._user and self._user.is_authenticated:
            self._user_profile = self._user_profile or UserProfile.objects.get(user=self.user)
            self._account = self._account or self.user_profile.account

        # basically repeats this entire set of logic but from inside
        # the chatbot property with whatever we have at this point.
        if not self._chatbot:
            self._chatbot = self.chatbot

        self.log_dump()

        if self._chatbot:
            self.set_to_cache(self._chatbot)
            return None

        self.helper_warning(
            f"__init__() failed to initialize self.chatbot with url={url}, name={name}, account={account}, chatbot_id={chatbot_id}"
        )

    def __str__(self):
        return str(self.chatbot) if self.chatbot else "undefined"

    @property
    def chatbot_id(self) -> int:
        return self._chatbot_id if self._chatbot_id else self.chatbot.id if self._chatbot else None

    @property
    def name(self):
        if self._name:
            return self._name

        if self._chatbot:
            self._name = self.chatbot.name

        if self.is_named_url:
            self._name = self.subdomain
        else:
            # covers a case like http://localhost:8000/chatbots/example/
            # where api_host == /chatbots/example/
            if self.api_host and "/chatbots/" in self.api_host:
                split_host = self.api_host.split("/") if self.api_host else None
                if split_host and len(split_host) > 2:
                    self._name = split_host[-2]
        return self._name

    @property
    def formatted_class_name(self):
        return formatted_text(self.__class__.__name__)

    def log_dump(self):
        if not self._chatbot and waffle.switch_is_active(
            SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHATBOT_HELPER_LOGGING
        ):
            return None

        horizontal_line = "-" * (80 - 15)
        logger.info("%s: %s", self.formatted_class_name, horizontal_line)
        logger.info("%s: INITIALIZATION DUMP.", self.formatted_class_name)
        logger.info("%s: %s", self.formatted_class_name, horizontal_line)
        logger.info(f"%s: chatbot={self.chatbot}", self.formatted_class_name)
        logger.info(f"%s: cache_key={self.cache_key}", self.formatted_class_name)
        logger.info(f"%s: account_number={self.account_number}", self.formatted_class_name)
        logger.info(f"%s: user={self.user}, account={self.account}", self.formatted_class_name)
        logger.info(f"%s: name={self.name}", self.formatted_class_name)

        logger.info(f"%s: url={self.url}", self.formatted_class_name)
        logger.info(f"%s: environment={self.environment}", self.formatted_class_name)
        logger.info(f"%s: domain={self.domain}, path={self.path}", self.formatted_class_name)
        logger.info(f"%s: subdomain={self.subdomain}", self.formatted_class_name)
        logger.info(f"%s: root_domain={self.root_domain}", self.formatted_class_name)
        logger.info(f"%s: api_subdomain={self.api_subdomain}, api_host={self.api_host}", self.formatted_class_name)
        logger.info(f"%s: customer_api_domain={self.customer_api_domain}", self.formatted_class_name)

        logger.info(f"%s: is_named_url={self.is_named_url}", self.formatted_class_name)
        logger.info(f"%s: is_sandbox_domain={self.is_sandbox_domain}", self.formatted_class_name)
        logger.info(f"%s: is_default_domain={self.is_default_domain}", self.formatted_class_name)
        logger.info(f"%s: is_custom_domain={self.is_custom_domain}", self.formatted_class_name)
        logger.info(f"%s: is_deployed={self.is_deployed}", self.formatted_class_name)
        logger.info(f"%s: is_valid={self.is_valid}", self.formatted_class_name)
        logger.info(f"%s: is_authentication_required={self.is_authentication_required}", self.formatted_class_name)
        logger.info("%s: %s", self.formatted_class_name, horizontal_line)

    def to_json(self):
        return {
            "url": self.url,
            "environment": self.environment,
            "domain": self.domain,
            "path": self.path,
            "root_domain": self.root_domain,
            "subdomain": self.subdomain,
            "api_subdomain": self.api_subdomain,
            "api_host": self.api_host,
            "customer_api_domain": self.customer_api_domain,
            "is_sandbox_domain": self.is_sandbox_domain,
            "is_default_domain": self.is_default_domain,
            "is_custom_domain": self.is_custom_domain,
            "is_named_url": self.is_named_url,
            "is_deployed": self.is_deployed,
            "is_valid": self.is_valid,
            "is_authentication_required": self.is_authentication_required,
            "user": self.user.username if self.user else None,
            "account": self.account.account_number if self.account else None,
            "chatbot": ChatBotSerializer(self.chatbot).data if self.chatbot else None,
        }

    @property
    def cache_key(self) -> str:
        """
        The cache key to use for this object. using private variable
        references to avoid infinite recursion.
        """
        if self._account_number and self._url:
            return f"{CACHE_PREFIX}_{self._account_number}_{self._url}"
        if self._chatbot_id:
            return f"{CACHE_PREFIX}_{self._chatbot_id}"
        return None

    @property
    def environment(self) -> str:
        """
        The environment to use for the URL.
        :return: The environment to use for the URL.

        examples:
        - alpha
        - local
        """
        return self._environment or smarter_settings.environment

    @property
    def url(self) -> str:
        """
        The URL to parse.
        :return: The URL to parse.

        examples:
        - https://alpha.platform.smarter.sh/api/v1/chatbots/1/chatbot/
        - http://example.com/contact/
        - https://hr.3141-5926-5359.alpha.api.smarter.sh/chatbot/
        - https://hr.smarter.querium.com/chatbot/
        """
        if self._url:
            return SmarterValidator.urlify(self._url, environment=smarter_settings.environment)
        self._url = (
            SmarterValidator.urlify(self.chatbot.url, environment=smarter_settings.environment)
            if self._chatbot
            else None
        )
        return self._url

    @property
    def parsed_url(self) -> ParseResult:
        if self.url:
            SmarterValidator.validate_url(self.url)
            return urlparse(self._url)
        return None

    @property
    def domain(self) -> str:
        """
        Extracts the domain from the URL.
        :return: The domain or None if not found.

        examples:
        - https://hr.3141-5926-5359.alpha.api.smarter.sh/chatbot/
          returns 'hr.3141-5926-5359.alpha.api.smarter.sh'
        """
        if self.url:
            return self.parsed_url.netloc
        return None

    @property
    def path(self) -> str:
        """
        Extracts the path from the URL.
        :return: The path or None if not found.

        examples:
        - https://hr.3141-5926-5359.alpha.api.smarter.sh/chatbot/
          returns '/chatbot/'
        """
        if not self.url:
            return None
        if self.parsed_url.path == "":
            return "/"
        return self.parsed_url.path

    @property
    def root_domain(self) -> str:
        """
        Extracts the root domain from the URL.
        :return: The root domain or None if not found.

        examples:
        - https://hr.3141-5926-5359.alpha.api.smarter.sh/chatbot/
          returns 'smarter.sh'
        """
        if not self.url:
            return None
        url = SmarterValidator.urlify(self.domain, environment=smarter_settings.environment) or ""
        subdomain = self.subdomain or ""
        return url.replace(f"{subdomain}.", "").replace("http://", "").replace("https://", "").replace("/", "")

    @property
    def subdomain(self) -> str:
        """
        Extracts the subdomain from the URL.
        :return: The subdomain or None if not found.

        examples:
        - https://hr.3141-5926-5359.alpha.api.smarter.sh/chatbot/
          returns 'hr.3141-5926-5359.alpha'
        """
        if not self.url:
            return None
        extracted = tldextract.extract(self.url)
        return extracted.subdomain

    # pylint: disable=R0911
    @property
    def account_number(self) -> str:
        """
        Extracts the account number from the URL.
        :return: The account number or None if not found.

        the account number needs to conform to the SmarterValidator.VALID_ACCOUNT_NUMBER_PATTERN
        and it needs to be the second segment of the subdomain of the URL.
        """
        if self._account_number:
            return self._account_number
        if self._account:
            self._account_number = self.account.account_number
            return self._account_number

        self._account_number = account_number_from_url(self.url)

        if self.is_sandbox_domain and not self._account_number:
            logger.debug("account_number() - sandbox domain")
            if self._chatbot:
                self._account_number = self.chatbot.account.account_number
            self._account_number = self._account_number

        if self.is_default_domain and not self._account_number:
            logger.debug("account_number() - default domain")
            self._account_number = self._account_number

        if self.is_custom_domain and not self._account_number:
            logger.debug("account_number() - custom domain")
            self._account_number = self._account_number or self.chatbot.account.account_number if self.chatbot else None

        if self._account_number:
            self._account = self._account or Account.objects.get(account_number=self._account_number)
            self.helper_logger(f"initialized self.account={self.account}")

        return self._account_number

    @property
    def api_subdomain(self) -> str:
        """
        Extracts the API subdomain from the URL.

        example: https://hr.3141-5926-5359.alpha.api.smarter.sh/chatbot/
        returns 'hr'
        """
        try:
            result = urlparse(self.url)
            domain_parts = result.netloc.split(".")
            return domain_parts[0]
        except TypeError:
            return None

    @property
    def api_host(self) -> str:
        """
        Returns the API host for a ChatBot API url.
        :return: The API host or None if not found.

        examples:
        - https://hr.3141-5926-5359.alpha.api.smarter.sh/chatbot/
          returns 'alpha.api.smarter.sh'
        - https://hr.smarter.querium.com/chatbot/
          return 'smarter.querium.com'
        """
        if self.is_default_domain:
            return self.customer_api_domain
        if self.is_custom_domain:
            domain_parts = self.domain.split(".")
            return ".".join(domain_parts[1:])
        if self.is_sandbox_domain:
            return self.path
        return None

    @property
    def customer_api_domain(self) -> str:
        """
        Returns the customer API domain for default ChatBot API urls.
        :return: The customer API domain or None if not found.

        examples:
        - alpha.api.smarter.sh
        - local.api.smarter.sh
        """
        return smarter_settings.customer_api_domain

    @property
    def is_sandbox_domain(self) -> bool:
        if not self.url:
            return False
        # best way to match: using a regular expression against the url pattern
        match = re.search(r"/api/v1/chatbots/(\d+)", self.url)
        if match:
            return True
        # an alternative way to match: looking for the environment domain name in the domain name
        return smarter_settings.environment_domain in self.domain

    @property
    def is_default_domain(self) -> bool:
        if not self.url:
            return False
        return self.customer_api_domain in self.url

    @property
    def is_custom_domain(self) -> bool:
        if not self.url:
            return False
        if self.is_default_domain:
            return False
        return self.chatbot_custom_domain is not None

    @property
    def is_deployed(self) -> bool:
        if not self.url:
            return False
        if self.chatbot:
            return self.chatbot.deployed
        return False

    @property
    def is_valid(self) -> bool:
        if self.chatbot is None:
            return False
        if self.user and self.user.is_authenticated and not self.user_profile:
            return False
        return True

    @property
    def is_authentication_required(self) -> bool:
        if ChatBotAPIKey.objects.filter(chatbot=self.chatbot, api_key__is_active=True).exists():
            return True
        return False

    @property
    def is_named_url(self) -> bool:
        """
        Returns True if the url is of the form https://example.3141-5926-5359.api.smarter.sh/
        """
        if not self.url:
            return False
        if not smarter_settings.customer_api_domain in self.url:
            self.helper_logger(
                f"customer_api_domain {smarter_settings.customer_api_domain} not found in url {self.url}"
            )
            return False
        if account_number_from_url(self.url):
            return True
        self.helper_logger(f"did not match account number regex {SMARTER_ACCOUNT_NUMBER_REGEX} against {self.url}")
        return False

    @property
    def chatbot(self) -> ChatBot:
        """
        Returns a lazy instance of the ChatBot
        """
        if self._chatbot:
            return self._chatbot

        if self.chatbot_id:
            try:
                self._chatbot = ChatBot.objects.get(id=self.chatbot_id)
                self.set_to_cache(self._chatbot)
            except ChatBot.DoesNotExist as e:
                raise SmarterValueError(f"ChatBot with id={self.chatbot_id} does not exist") from e
            return self._chatbot

        admin_account = smarter_admin_user_profile().account

        if self.account and self.name:
            try:
                self._chatbot = ChatBot.objects.get(account=self.account, name=self.name)
                self.set_to_cache(self._chatbot)
                self.helper_logger(
                    f"initialized chatbot {self._chatbot} from account {self.account} and name {self.name}"
                )
            except ChatBot.DoesNotExist:
                try:
                    self._chatbot = ChatBot.objects.get(account=admin_account, name=self.name)
                    self.set_to_cache(self._chatbot)
                    self.helper_logger(
                        f"initialized chatbot {self._chatbot} from account {admin_account} and name {self.name}"
                    )
                except ChatBot.DoesNotExist:
                    self.helper_warning(f"didn't find chatbot for account: {self.account} name: {self.name}")
            return self._chatbot

        if self.is_sandbox_domain:
            # example: http://127.0.0.1:8000/api/v1/chatbots/1/chatbot/
            match = re.search(r"/api/v1/chatbots/(\d+)", self.url)
            if match:
                chatbot_id = int(match.group(1))
                self.helper_logger(f"matched ChatBot id {chatbot_id} from regular expression against {self.url}")
                try:
                    self._chatbot = ChatBot.objects.get(id=chatbot_id)
                    self.set_to_cache(self._chatbot)
                    self.helper_logger(f"initialized chatbot {self._chatbot} from sandbox domain {self.url}")
                except ChatBot.DoesNotExist as e:
                    self.helper_warning(f"ChatBot {chatbot_id} not found")
                    raise ChatBot.DoesNotExist from e
            return self._chatbot

        if self.is_default_domain:
            try:
                self._chatbot = ChatBot.objects.get(account=self.account, name=self.api_subdomain, deployed=True)
                self.set_to_cache(self._chatbot)
                self.helper_logger(
                    f"initialized chatbot {self._chatbot} from account {self.account} and api_subdomain {self.api_subdomain}"
                )
            except ChatBot.DoesNotExist:
                try:
                    self._chatbot = ChatBot.objects.get(account=admin_account, name=self.api_subdomain, deployed=True)
                    self.set_to_cache(self._chatbot)
                    self.helper_logger(
                        f"initialized chatbot {self._chatbot} from account {admin_account} and name {self.api_subdomain}"
                    )
                except ChatBot.DoesNotExist as e:
                    self.helper_warning(
                        f"didn't find chatbot for default_domain with account: {self.account} name: {self.api_subdomain} {self.url}"
                    )
                    raise ChatBot.DoesNotExist from e
            return self._chatbot

        if self.is_custom_domain:
            try:
                self._chatbot = ChatBot.objects.get(custom_domain=self.chatbot_custom_domain, deployed=True)
                self.set_to_cache(self._chatbot)
                self.helper_logger(
                    message=f"initialized chatbot {self._chatbot} from custom domain {self.chatbot_custom_domain}"
                )
            except ChatBot.DoesNotExist as e:
                raise ChatBot.DoesNotExist from e
            return self._chatbot

        if not self._chatbot:
            # this scenario would most likely occur when running a chat session from the cli.
            # The cli uses the url_chatbot property from chat_config to get the chatbot url, and this
            # property does not evaluate the deployment state as part of its logic.
            if self.account and self.api_subdomain:
                try:
                    self._chatbot = ChatBot.objects.get(account=self.account, name=self.api_subdomain)
                    self.set_to_cache(self._chatbot)
                except ChatBot.DoesNotExist:
                    try:
                        self._chatbot = ChatBot.objects.get(account=admin_account, name=self.api_subdomain)
                        self.set_to_cache(self._chatbot)
                        self.helper_logger(
                            message=f"initialized chatbot {self._chatbot} from account {admin_account} and name {self.api_subdomain}"
                        )
                    except ChatBot.DoesNotExist as e:
                        self.helper_warning(
                            f"didn't find chatbot for account: {self.account} name: {self.api_subdomain} {self.url}"
                        )
                        raise ChatBot.DoesNotExist from e
                if not self._chatbot.deployed:
                    self.helper_warning(f"Initializing with chatbot {self._chatbot}, which is not deployed.")
                return self._chatbot

        if self._chatbot:
            self.helper_logger(f"chatbot() initialized: {self._chatbot}")
        return self._chatbot

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

        # this is a cheaper operation than the one below
        if self.is_default_domain:
            return None

        if not self.url:
            return None

        domain_parts = self.domain.split(".")
        domain_name = ".".join(domain_parts[1:])
        try:
            self._chatbot_custom_domain = ChatBotCustomDomain.objects.get(domain_name=domain_name)
        except ChatBotCustomDomain.DoesNotExist:
            return None

        return self._chatbot_custom_domain

    @classmethod
    def get_by_id(cls, chatbot_id: int) -> ChatBot:
        """
        Returns a ChatBot object by its id.
        """
        cache_key = f"{CACHE_PREFIX}_{chatbot_id}"
        chatbot: ChatBot = cache.get(cache_key)
        if chatbot:
            return chatbot
        try:
            chatbot = cls.objects.get(id=chatbot_id)
            return chatbot
        except cls.DoesNotExist:
            return None

    def get_from_cache(self) -> ChatBot:
        """
        Returns a ChatBot object from the cache.
        """
        if self.cache_key:
            chatbot: ChatBot = cache.get(self.cache_key) if self.cache_key else None
            if chatbot:
                self.helper_logger(message=f"returning cached chatbot {chatbot.url}")
                return chatbot
        return None

    def set_to_cache(self, chatbot: ChatBot):
        """
        Caches a ChatBot object.
        """
        cache.set(key=self.cache_key, value=chatbot, timeout=settings.SMARTER_CHATBOT_CACHE_EXPIRATION)
        self.helper_logger(
            message=f"cached {self.cache_key} timeout: {settings.SMARTER_CHATBOT_CACHE_EXPIRATION} chatbot: {chatbot}"
        )

    def helper_logger(self, message: str):
        """
        Create a log entry
        """
        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHATBOT_HELPER_LOGGING):
            logger.info(f"{self.formatted_class_name}: {message}")

    def helper_warning(self, message: str):
        """
        Create a log entry
        """
        logger.warning(f"{self.formatted_class_name}: {message}")

    def clean_url(self, url: str) -> str:
        """
        Clean the url of any query strings and trailing '/config/' strings.
        """
        # remove any query strings from url and also prune any trailing '/config/' from the url
        retval = self.parsed_url._replace(query="").geturl()
        if retval.endswith("/config/"):
            retval = retval[:-8]
        return retval
