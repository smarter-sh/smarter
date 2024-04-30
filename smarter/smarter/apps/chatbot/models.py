# pylint: disable=W0613,C0115
"""All models for the OpenAI Function Calling API app."""
import logging
import re
from typing import List, Type
from urllib.parse import urljoin, urlparse

import tldextract
import waffle
from django.conf import settings
from django.core.cache import cache
from django.db import models

# our stuff
from smarter.apps.account.models import Account, SmarterAuthToken, UserProfile
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.plugin.static import PluginStatic
from smarter.common.conf import settings as smarter_settings
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django.model_helpers import TimestampedModel
from smarter.lib.django.user import User, UserType
from smarter.lib.django.validators import SmarterValidator


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
        return str(self.domain_name)


class ChatBotCustomDomainDNS(TimestampedModel):
    """ChatBot DNS Records for a ChatBot DNS Host."""

    class Meta:
        verbose_name_plural = "ChatBot Custom Domain DNS"

    custom_domain = models.ForeignKey(ChatBotCustomDomain, on_delete=models.CASCADE)
    record_name = models.CharField(max_length=255)
    record_type = models.CharField(max_length=255)
    record_value = models.CharField(max_length=255)
    record_ttl = models.IntegerField(default=600, blank=True, null=True)


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

    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    subdomain = models.ForeignKey(ChatBotCustomDomainDNS, on_delete=models.CASCADE, blank=True, null=True)
    custom_domain = models.ForeignKey(ChatBotCustomDomain, on_delete=models.CASCADE, blank=True, null=True)
    deployed = models.BooleanField(default=False, blank=True, null=True)
    default_model = models.CharField(
        default=smarter_settings.openai_default_model, max_length=255, blank=True, null=True
    )
    default_temperature = models.FloatField(default=smarter_settings.openai_default_temperature, blank=True, null=True)
    default_max_tokens = models.IntegerField(default=smarter_settings.openai_default_max_tokens, blank=True, null=True)

    app_name = models.CharField(default="chatbot", max_length=255, blank=True, null=True)
    app_assistant = models.CharField(default="Smarter", max_length=255, blank=True, null=True)
    app_welcome_message = models.CharField(default="Welcome to the chatbot!", max_length=255, blank=True, null=True)
    app_example_prompts = models.JSONField(default=list, blank=True, null=True)
    app_placeholder = models.CharField(default="Type something here...", max_length=255, blank=True, null=True)
    app_info_url = models.URLField(default="https://smarter.sh", blank=True, null=True)
    app_background_image_url = models.URLField(blank=True, null=True)
    app_logo_url = models.URLField(blank=True, null=True)
    app_file_attachment = models.BooleanField(default=False, blank=True, null=True)

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
        return SmarterValidator.urlify(self.default_host, scheme=self.scheme)

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
            return SmarterValidator.urlify(self.custom_host, scheme=self.scheme)
        return None

    @property
    def sandbox_host(self):
        """
        return 'alpha.api.smarter.sh/api/v0/chatbots/1/'
        """
        domain = f"{smarter_settings.environment_domain}/api/v0/chatbots/{self.id}/"
        SmarterValidator.validate_domain(domain)
        return domain

    @property
    def sandbox_url(self):
        """
        return 'https://alpha.api.smarter.sh/api/v0/chatbots/1/'
        """
        return SmarterValidator.urlify(self.sandbox_host, scheme=self.scheme)

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
        return urljoin(self.url, "chatbot/")

    @property
    def url_chatapp(self):
        return urljoin(self.url, "chatapp/")

    @staticmethod
    def get_by_request(request):
        host = request.get_host()
        url = SmarterValidator.urlify(host)
        parsed_host = urlparse(url)
        host = parsed_host.hostname
        return ChatBot.get_by_url(url)

    @staticmethod
    # @cache_results(timeout=600)
    def get_by_url(url: str):
        logger.debug("ChatBot() get_by_url: %s", url)
        url = SmarterValidator.urlify(url)
        retval = ChatBotHelper(url).chatbot
        return retval

    def mode(self, url: str) -> str:
        logger.debug("mode: %s", url)
        if not url:
            return self.Modes.UNKNOWN
        SmarterValidator.validate_url(url)
        url = SmarterValidator.urlify(url)
        custom_url = SmarterValidator.urlify(self.custom_host)
        default_url = SmarterValidator.urlify(self.default_host)
        sandbox_url = SmarterValidator.urlify(self.sandbox_host)
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
        super().save(*args, **kwargs)

    def __str__(self):
        return self.url


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

    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE)
    plugin_meta = models.ForeignKey(PluginMeta, on_delete=models.CASCADE)

    def __str__(self):
        return f"{str(self.chatbot.url)} - {str(self.plugin_meta.name)}"

    @property
    def plugin(self) -> PluginStatic:
        return PluginStatic(plugin_meta=self.plugin_meta)

    @classmethod
    def load(cls: Type["ChatBotPlugin"], chatbot: ChatBot, data) -> "ChatBotPlugin":
        """Load (aka import) a plugin from a data file in yaml or json format."""
        user_profile = UserProfile.admin_for_account(chatbot.account)
        plugin = PluginStatic(data=data, user_profile=user_profile)
        return cls.objects.create(chatbot=chatbot, plugin_meta=plugin.meta)

    @classmethod
    def plugins(cls, chatbot: ChatBot) -> List[PluginStatic]:
        chatbot_plugins = cls.objects.filter(chatbot=chatbot)
        retval = []
        for chatbot_plugin in chatbot_plugins:
            retval.append(PluginStatic(plugin_meta=chatbot_plugin.plugin_meta))
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


class ChatBotRequests(TimestampedModel):
    """List of Requests for a ChatBot"""

    class Meta:
        verbose_name_plural = "ChatBot Prompt History"

    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE)
    request = models.JSONField(blank=True, null=True)
    is_aggregation = models.BooleanField(default=False, blank=True, null=True)


# pylint: disable=too-many-instance-attributes,too-many-public-methods
class ChatBotHelper:
    """Maps urls and attribute data to their respective ChatBot models.
    Abstracts url parsing logic so that we can use it in multiple
    places: inside this module, in middleware, in Views, etc.

    Also caches the ChatBot object for a given url so that we don't have to
    parse the url multiple times.

    examples of valid urls:
    - https://hr.3141-5926-5359.alpha.api.smarter.sh/chatbot/
    - https://hr.smarter.querium.com/chatbot/
    """

    CACHE_PREFIX = "ChatBotHelper_"

    _cache_key: str = None
    _url: str = None
    _account_number: str = None
    _environment: str = None
    _account: Account = None
    _user: UserType = None
    _user_profile: UserProfile = None
    _chatbot: ChatBot = None
    _chatbot_custom_domain: ChatBotCustomDomain = None

    # pylint: disable=W1203,R0913,R0915,R0912
    # mcdaniel apr-2024 TODO: refactor this class to reduce complexity, and memory usage.
    def __init__(
        self, url: str = None, user: UserType = None, account: Account = None, name: str = None, environment: str = None
    ):
        """
        Constructor for ChatBotHelper.
        :param url: The URL to parse.
        :param environment: The environment to use for the URL. (for unit testing only)
        """
        if url:
            SmarterValidator.validate_url(url)  # raises ValidationError if url is invalid
            url = SmarterValidator.urlify(
                url
            )  # normalizes the url so that we dont find ourselves working with variations of the same url
            self._url = url

        # 1. return a cached object if we have one.
        #    first, check to see if the cache key exists bc we also cache and return None values
        self._cache_key = f"{self.CACHE_PREFIX}_{self.url}"
        if self.cache_key in cache:
            self._chatbot = cache.get(self.cache_key)
            if self._chatbot and waffle.switch_is_active("chatbothelper_logging"):
                logger.info(
                    "%s: %s, account: %s for url: %s",
                    formatted_text("ChatBotHelper: returning cached chatbot"),
                    self.chatbot.name,
                    self.chatbot.account.account_number,
                    self.url,
                )

            # most calls arrive here, because in most cases the url is not a
            # chatbot url and its already cached.
            return None

        if waffle.switch_is_active("chatbothelper_logging"):
            logger.info("ChatBotHelper: __init__()")

        # 2. take a wild swing at initializing the chatbot using the built-in property logic
        self._chatbot = self.chatbot

        if environment:
            self._environment = environment
            if waffle.switch_is_active("chatbothelper_logging"):
                logger.info(f"ChatBotHelper: initialized self.environment={self.environment}")

        if not self._chatbot and user and not self._user:
            self._user = user
            if waffle.switch_is_active("chatbothelper_logging"):
                logger.info(f"ChatBotHelper: initialized self.user={self.user}")
            self._user_profile = UserProfile.objects.get(user=self.user)
            if waffle.switch_is_active("chatbothelper_logging"):
                logger.info(f"ChatBotHelper: initialized self.user_profile from self.user={self.user}")
            self._account = self.user_profile.account
            if waffle.switch_is_active("chatbothelper_logging"):
                logger.info(f"ChatBotHelper: initialized self.account from self.user_profile={self.user_profile}")

        if not self._chatbot and account and not self._account:
            self._account = account
            if waffle.switch_is_active("chatbothelper_logging"):
                logger.info(f"ChatBotHelper: initialized self.account={self.account}")

        if not self._chatbot and self._user and self._account and not self._user_profile:
            self._user_profile, created = UserProfile.objects.get_or_create(user=self._user, account=self._account)
            if created:
                logger.warning(f"ChatBotHelper: created missing user_profile={self.user_profile}")
            self._account = self.user_profile.account
            if waffle.switch_is_active("chatbothelper_logging"):
                logger.info(f"ChatBotHelper: initialized self.account={self.account}")

        if not self._chatbot and self._account and name:
            try:
                self._chatbot = ChatBot.objects.get(account=self._account, name=name)
                if waffle.switch_is_active("chatbothelper_logging"):
                    logger.info(f"ChatBotHelper: initialized self.chatbot={self.chatbot}")
            except ChatBot.DoesNotExist:
                pass

        if not self._chatbot and self._account and self.api_subdomain:
            try:
                self._chatbot = ChatBot.objects.get(account=self._account, name=self.api_subdomain)
                if waffle.switch_is_active("chatbothelper_logging"):
                    logger.info(f"ChatBotHelper: initialized self.chatbot={self.chatbot}")
            except ChatBot.DoesNotExist:
                pass

        if not self._chatbot and self.account_number and self.api_subdomain:
            try:
                self._chatbot = ChatBot.objects.get(account=self.account, name=self.api_subdomain)
                if waffle.switch_is_active("chatbothelper_logging"):
                    logger.info(f"ChatBotHelper: initialized self.chatbot={self.chatbot}")
            except ChatBot.DoesNotExist:
                pass

        if self._chatbot and waffle.switch_is_active("chatbothelper_logging"):
            self.log_dump()

        # cache the url so we don't have to parse it again
        cache.set(key=self.cache_key, value=self._chatbot, timeout=settings.SMARTER_CHATBOT_CACHE_EXPIRATION)
        if waffle.switch_is_active("chatbothelper_logging"):
            logger.info("%s - %s", formatted_text("ChatBotHelper: cached url"), self.url)
        return None

    def __str__(self):
        return self.url

    def log_dump(self):
        logger.info("ChatBotHelper: %s", "-" * (80 - 15))
        logger.info("ChatBotHelper: INITIALIZED.")
        logger.info("ChatBotHelper: %s", "-" * (80 - 15))
        logger.info(f"ChatBotHelper: chatbot={self.chatbot}")
        logger.info(f"ChatBotHelper: account_number={self.account_number}")
        logger.info(f"ChatBotHelper: user={self.user}, account={self.account}")

        logger.info(f"ChatBotHelper: url={self.url}, environment={self.environment}")
        logger.info(f"ChatBotHelper: domain={self.domain}, path={self.path}")
        logger.info(f"ChatBotHelper: subdomain={self.subdomain}")
        logger.info(f"ChatBotHelper: root_domain={self.root_domain}")
        logger.info(f"ChatBotHelper: api_subdomain={self.api_subdomain}, api_host={self.api_host}")
        logger.info(f"ChatBotHelper: customer_api_domain={self.customer_api_domain}")

        logger.info(f"ChatBotHelper: is_sandbox_domain={self.is_sandbox_domain}")
        logger.info(f"ChatBotHelper: is_default_domain={self.is_default_domain}")
        logger.info(f"ChatBotHelper: is_custom_domain={self.is_custom_domain}")
        logger.info(f"ChatBotHelper: is_deployed={self.is_deployed}")
        logger.info(f"ChatBotHelper: is_valid={self.is_valid}")
        logger.info(f"ChatBotHelper: is_authentication_required={self.is_authentication_required}")
        logger.info("ChatBotHelper: %s", "-" * (80 - 15))

    def to_json(self):
        return {
            "url": self.url,
            "environment": self.environment,
            "domain": self.domain,
            "path": self.path,
            "root_domain": self.root_domain,
            "subdomain": self.subdomain,
            "account_number": self.account_number,
            "api_subdomain": self.api_subdomain,
            "api_host": self.api_host,
            "customer_api_domain": self.customer_api_domain,
            "is_sandbox_domain": self.is_sandbox_domain,
            "is_default_domain": self.is_default_domain,
            "is_custom_domain": self.is_custom_domain,
            "is_deployed": self.is_deployed,
            "is_valid": self.is_valid,
            "is_authentication_required": self.is_authentication_required,
            "user": self.user.username if self.user else None,
            "account": self.account.account_number if self.account else None,
            "chatbot": self.chatbot.name if self.chatbot else None,
        }

    @property
    def cache_key(self) -> str:
        return self._cache_key

    @property
    def parsed_url(self):
        if self.url:
            return urlparse(self._url)
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
        - https://alpha.platform.smarter.sh/api/v0/chatbots/1/chatbot/
        - http://example.com/contact/
        - https://hr.3141-5926-5359.alpha.api.smarter.sh/chatbot/
        - https://hr.smarter.querium.com/chatbot/
        """
        if self._url:
            return self._url
        if self._chatbot:
            self._url = self.chatbot.url
        return self._url

    @property
    def domain(self) -> str:
        """
        Extracts the domain from the URL.
        :return: The domain or None if not found.

        examples:
        - https://hr.3141-5926-5359.alpha.api.smarter.sh/chatbot/
          returns 'hr.3141-5926-5359.alpha.api.smarter.sh'
        """
        if not self.url:
            return None
        return self.parsed_url.netloc

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
        url = SmarterValidator.urlify(self.domain) or ""
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

        def from_url(url: str) -> str:
            pattern = r"\d{4}-\d{4}-\d{4}"
            match = re.search(pattern, url)
            retval = match.group(0) if match else None
            if retval:
                try:
                    self._account = Account.objects.get(account_number=retval)
                    if waffle.switch_is_active("chatbothelper_logging"):
                        logger.info(f"ChatBotHelper: initialized self.account={self.account}")
                except Account.DoesNotExist:
                    logger.warning(f"Account {retval} not found")
                    self._account_number = None
                    return None
            return retval

        if self.is_sandbox_domain:
            logger.debug("account_number() - sandbox domain")
            if self._chatbot:
                return self._chatbot.account.account_number
            self._account_number = from_url(self.url)
            return self._account_number

        if self.is_default_domain:
            logger.debug("account_number() - default domain")
            self._account_number = from_url(self.url)
            return self._account_number

        if self.is_custom_domain:
            logger.debug("account_number() - custom domain")
            self._account_number = self.chatbot.account.account_number if self.chatbot else None
            return self._account_number

        if self._account_number:
            self._account = Account.objects.get(account_number=self._account_number)
            if waffle.switch_is_active("chatbothelper_logging"):
                logger.info(f"ChatBotHelper: initialized self.account={self.account}")

        return self._account_number

    @property
    def api_subdomain(self) -> str:
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
        match = re.search(r"/api/v0/chatbots/(\d+)", self.url)
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
        if self.user and not self.user_profile:
            return False
        return True

    @property
    def is_authentication_required(self) -> bool:
        if ChatBotAPIKey.objects.filter(chatbot=self.chatbot, api_key__is_active=True).exists():
            return True
        return False

    @property
    def user_profile(self) -> UserProfile:
        """
        Returns the user profile for the ChatBot API url.
        :return: The user profile or None if not found.
        """
        if self._user_profile:
            return self._user_profile
        if self._user and self._account:
            try:
                self._user_profile = UserProfile.objects.get(user=self.user, account=self.account)
                if self._user_profile and waffle.switch_is_active("chatbothelper_logging"):
                    logger.info(
                        f"ChatBotHelper: initialized UserProfile: {self._user_profile} from self.user and self.account"
                    )
                return self._user_profile
            except UserProfile.DoesNotExist:
                return None
        return None

    @property
    def user(self) -> UserType:
        """
        Returns the user for the ChatBot API url.
        :return: The user or None if not found.
        """
        if isinstance(self._user, User):
            return self._user
        if self.account:
            self._user = UserProfile.admin_for_account(self.account)
        if self._user and waffle.switch_is_active("chatbothelper_logging"):
            logger.info(
                f"ChatBotHelper: initialized user {self._user} with admin for account {self.account.account_number}"
            )
        return self._user

    @property
    def account(self) -> Account:
        """
        Returns a lazy instance of the Account
        """
        if self._account:
            return self._account
        if self._chatbot:
            self._account = self.chatbot.account
            if waffle.switch_is_active("chatbothelper_logging"):
                logger.info(f"ChatBotHelper: initialized account {self._account} from chatbot {self._chatbot}")
            return self._account
        if self._user_profile:
            self._account = self.user_profile.account
            if waffle.switch_is_active("chatbothelper_logging"):
                logger.info(
                    f"ChatBotHelper: initialized account {self._account} from user_profile {self._user_profile}"
                )
            return self._account
        if self._user:
            self._user_profile = UserProfile.objects.get(user=self.user)
            self._account = self.user_profile.account
            if waffle.switch_is_active("chatbothelper_logging"):
                logger.info(
                    f"ChatBotHelper: initialized account {self._account} from user {self.user} and user_profile {self.user_profile}"
                )
        if self.account_number:
            try:
                self._account = Account.objects.get(account_number=self.account_number)
                if waffle.switch_is_active("chatbothelper_logging"):
                    logger.info(
                        f"ChatBotHelper: used account number {self.account_number} to initialize self.account={self.account}"
                    )
            except Account.DoesNotExist:
                logger.warning(f"ChatBotHelper: account {self.account_number} not found")
                if self._user_profile:
                    logger.warning(
                        f"ChatBotHelper: User Profile {self._user_profile} is linked to account {self._user_profile.account}"
                    )
                return None
        if self._account:
            logger.info(f"ChatBotHelper: initialized account: {self._account}")
        return self._account

    @property
    def chatbot(self) -> ChatBot:
        """
        Returns a lazy instance of the ChatBot
        """
        if self._chatbot:
            return self._chatbot

        if self.is_sandbox_domain:
            # example: http://127.0.0.1:8000/api/v0/chatbots/1/chatbot/
            match = re.search(r"/api/v0/chatbots/(\d+)", self.url)
            if match:
                chatbot_id = int(match.group(1))
                if waffle.switch_is_active("chatbothelper_logging"):
                    logger.info(
                        f"ChatBotHelper: matched ChatBot id {chatbot_id} from regular expression against {self.url}"
                    )
                try:
                    self._chatbot = ChatBot.objects.get(id=chatbot_id)
                    if waffle.switch_is_active("chatbothelper_logging"):
                        logger.info(
                            f"ChatBotHelper: initialized chatbot {self._chatbot} from sandbox domain {self.url}"
                        )
                    return self._chatbot
                except ChatBot.DoesNotExist:
                    logger.warning(f"ChatBot {chatbot_id} not found")
                    return None
            return None

        if self.is_default_domain:
            try:
                self._chatbot = ChatBot.objects.get(account=self.account, name=self.api_subdomain, deployed=True)
                if waffle.switch_is_active("chatbothelper_logging"):
                    logger.info(
                        f"ChatBotHelper: initialized chatbot {self._chatbot} from account {self.account} and api_subdomain {self.api_subdomain}"
                    )
                return self._chatbot
            except ChatBot.DoesNotExist:
                logger.warning(
                    f"didn't find chatbot for default_domain with account: {self.account} name: {self.api_subdomain} {self.url}"
                )
                return None

        if self.is_custom_domain:
            try:
                self._chatbot = ChatBot.objects.get(custom_domain=self.chatbot_custom_domain, deployed=True)
                if waffle.switch_is_active("chatbothelper_logging"):
                    logger.info(
                        f"ChatBotHelper: initialized chatbot {self._chatbot} from custom domain {self.chatbot_custom_domain}"
                    )
                return self._chatbot
            except ChatBot.DoesNotExist:
                return None

        if self._chatbot:
            logger.info(f"ChatBotHelper: initialized ChatBot: {self._chatbot}")
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
