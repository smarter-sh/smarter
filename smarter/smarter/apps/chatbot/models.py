# pylint: disable=W0613,C0115
"""All models for the OpenAI Function Calling API app."""
import re
from typing import List, Type
from urllib.parse import urlparse

import tldextract
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import models

from smarter.apps.account.models import Account, APIKey, UserProfile
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.plugin import Plugin

# our stuff
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_CUSTOMER_API_SUBDOMAIN
from smarter.common.helpers.model_helpers import TimestampedModel
from smarter.common.validators import SmarterValidator

from .utils import cache_results


# -----------------------------------------------------------------------------
# ChatBot Models. These implement a ChatBot API for a customer account.
# -----------------------------------------------------------------------------
class ChatBotCustomDomain(TimestampedModel):
    """A ChatBot DNS Host for a customer account. Linked to an AWS Hosted Zone."""

    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    aws_hosted_zone_id = models.CharField(max_length=255)
    domain_name = models.CharField(max_length=255)
    is_verified = models.BooleanField(default=False, blank=True, null=True)

    @classmethod
    def get_verified_domains(cls):
        # Try to get the list from cache
        cache_expiration = 15 * 60  # 15 minutes
        verified_domains = cache.get("chatbot_verified_custom_domains")

        # If the list is not in cache, fetch it from the database
        if not verified_domains:
            verified_domains = list(cls.objects.filter(is_verified=True).values_list("domain_name", flat=True))
            # Store the list in cache with a timeout of 15 minutes
            cache.set("chatbot_verified_custom_domains", verified_domains, cache_expiration)

        return verified_domains

    def save(self, *args, **kwargs):
        if self.domain_name:
            SmarterValidator.validate_domain(self.domain_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.domain_name)


class ChatBotCustomDomainDNS(TimestampedModel):
    """ChatBot DNS Records for a ChatBot DNS Host."""

    custom_domain = models.ForeignKey(ChatBotCustomDomain, on_delete=models.CASCADE)
    record_name = models.CharField(max_length=255)
    record_type = models.CharField(max_length=255)
    record_value = models.CharField(max_length=255)
    record_ttl = models.IntegerField(default=600, blank=True, null=True)


class ChatBot(TimestampedModel):
    """A ChatBot API for a customer account."""

    url_validator = URLValidator()

    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    subdomain = models.ForeignKey(ChatBotCustomDomainDNS, on_delete=models.CASCADE, blank=True, null=True)
    custom_domain = models.ForeignKey(ChatBotCustomDomain, on_delete=models.CASCADE, blank=True, null=True)
    deployed = models.BooleanField(default=False, blank=True, null=True)

    @staticmethod
    @cache_results(timeout=60 * 60)
    def get_by_url(url: str):
        return ChatBotApiUrlHelper().get_by_url(url)

    def save(self, *args, **kwargs):
        if not self.custom_domain:
            try:
                self.url_validator("http://" + self.hostname)
            except ValidationError as e:
                raise ValidationError(f"Invalid domain name {self.hostname}") from e
        super().save(*args, **kwargs)

    def __str__(self):
        return self.hostname

    @property
    def default_host(self):
        retval = f"{self.name}.{self.account.account_number}.{smarter_settings.customer_api_domain}"
        url = f"https://{retval}/"
        self.url_validator(url)
        return retval

    @property
    def custom_host(self):
        if self.custom_domain and self.custom_domain.is_verified:
            retval = f"{self.name}.{self.custom_domain.domain_name}"
            url = f"https://{retval}/"
            self.url_validator(url)
            return retval
        return None

    @property
    def hostname(self):
        return self.custom_host or self.default_host

    @property
    def url(self):
        return f"https://{self.hostname}/"


class ChatBotAPIKey(TimestampedModel):
    """Map of API keys for a ChatBot"""

    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE)
    api_key = models.ForeignKey(APIKey, on_delete=models.CASCADE)


class ChatBotPlugin(TimestampedModel):
    """List of Plugins for a ChatBot"""

    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE)
    plugin_meta = models.ForeignKey(PluginMeta, on_delete=models.CASCADE)

    @property
    def plugin(self) -> Plugin:
        return Plugin(plugin_meta=self.plugin_meta)

    @classmethod
    def load(cls: Type["ChatBotPlugin"], chatbot: ChatBot, data) -> "ChatBotPlugin":
        """Load (aka import) a plugin from a data file in yaml or json format."""
        user_profile = UserProfile.admin_for_account(chatbot.account)
        plugin = Plugin(data=data, user_profile=user_profile)
        return cls.objects.create(chatbot=chatbot, plugin_meta=plugin.meta)

    @classmethod
    def plugins(cls, chatbot: ChatBot) -> List[Plugin]:
        chatbot_plugins = cls.objects.filter(chatbot=chatbot)
        retval = []
        for chatbot_plugin in chatbot_plugins:
            retval.append(Plugin(plugin_meta=chatbot_plugin.plugin_meta))
        return retval


class ChatBotFunctions(TimestampedModel):
    """List of Functions for a ChatBot"""

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

    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE)
    request = models.JSONField(blank=True, null=True)
    is_aggregation = models.BooleanField(default=False, blank=True, null=True)


class ChatBotApiUrlHelper:
    """Helper class for ChatBot models. Abstracts url parsing logic so that we
    can use it in multiple places: this module, middleware, views, etc.

    examples of valid urls:
    - https://hr.3141-5926-5359.alpha.api.smarter.sh/chatbot/
    - https://hr.smarter.querium.com/chatbot/
    """

    _url: str = None
    _account_number: str = None
    _environment: str = None
    _account: Account = None
    _chatbot: ChatBot = None
    _chatbot_custom_domain: ChatBotCustomDomain = None

    def __init__(self, url: str = None, environment: str = None):
        """
        Constructor for ChatBotApiUrlHelper.
        :param url: The URL to parse.
        :param environment: The environment to use for the URL. (for unit testing only)
        """
        SmarterValidator.validate_url(url)
        self._url = url
        self._environment = environment
        self.parsed_url = urlparse(url)

    @property
    def environment(self) -> str:
        """
        The environment to use for the URL.
        :return: The environment to use for the URL.

        examples:
        - alpha
        - local
        """
        return self._environment

    @property
    def url(self) -> str:
        """
        The URL to parse.
        :return: The URL to parse.

        examples:
        - http://example.com/contact/
        - https://hr.3141-5926-5359.alpha.api.smarter.sh/chatbot/
        - https://hr.smarter.querium.com/chatbot/
        """
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
          returns 'api.smarter.sh'
        """
        if not self.url:
            return None
        extracted = tldextract.extract(self.url)
        return f"{extracted.domain}.{extracted.suffix}"

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

        if self.is_default_domain:
            account_number: str = None
            search_pattern = SmarterValidator.VALID_ACCOUNT_NUMBER_PATTERN.lstrip("^").rstrip("$")
            search_result = re.search(search_pattern, self.url)
            account_number = search_result.group(0)

            subdomain_parts = self.subdomain.split(".")
            if len(subdomain_parts) < 2:
                return None
            if account_number == subdomain_parts[1]:
                self._account_number = account_number
                return self._account_number
            return None

        if self.is_custom_domain:
            self._account_number = self.chatbot.account.account_number if self.chatbot else None
            return self._account_number
        return None

    @property
    def api_subdomain(self) -> str:
        if not self.url:
            return None
        subdomain_parts = self.subdomain.split(".")
        if len(subdomain_parts) < 2:
            return None
        return subdomain_parts[0]

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
        if not self.url:
            return None
        if self.environment:
            return f"{self.environment}.{SMARTER_CUSTOMER_API_SUBDOMAIN}.{smarter_settings.root_domain}"
        return smarter_settings.customer_api_domain

    @property
    def is_default_domain(self) -> bool:
        if not self.url:
            return False
        return self.customer_api_domain in self.url

    @property
    def is_custom_domain(self) -> bool:
        if self.is_default_domain:
            return False
        return self.chatbot_custom_domain is not None

    @property
    def is_deployed(self) -> bool:
        if self.chatbot:
            return self.chatbot.deployed
        return False

    @property
    def account(self) -> Account:
        """
        Returns a lazy instance of the Account
        """
        if self._account:
            return self._account
        if self.account_number:
            try:
                self._account = Account.objects.get(account_number=self.account_number)
            except Account.DoesNotExist:
                return None
        return self._account

    @property
    def chatbot(self) -> ChatBot:
        """
        Returns a lazy instance of the ChatBot
        """
        if self._chatbot:
            return self._chatbot

        if self.is_default_domain:
            try:
                self._chatbot = ChatBot.objects.get(account=self.account, name=self.api_subdomain, deployed=True)
            except ChatBot.DoesNotExist:
                return None

        if self.is_custom_domain:
            try:
                self._chatbot = ChatBot.objects.get(custom_domain=self.chatbot_custom_domain, deployed=True)
            except ChatBot.DoesNotExist:
                return None

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

        domain_parts = self.domain.split(".")
        domain_name = ".".join(domain_parts[1:])
        try:
            self._chatbot_custom_domain = ChatBotCustomDomain.objects.get(domain_name=domain_name)
        except ChatBotCustomDomain.DoesNotExist:
            return None

        return self._chatbot_custom_domain
