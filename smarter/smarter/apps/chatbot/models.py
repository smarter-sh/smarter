# -*- coding: utf-8 -*-
# pylint: disable=W0613,C0115
"""All models for the OpenAI Function Calling API app."""
import re
from typing import List, Type

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import models

from smarter.apps.account.models import Account, APIKey, UserProfile
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.plugin import Plugin

# our stuff
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import VALID_DOMAIN_PATTERN
from smarter.common.model_utils import TimestampedModel


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
            if re.match(VALID_DOMAIN_PATTERN, self.domain_name) is None:
                raise ValidationError(f"Invalid domain name: {self.domain_name}")
        super().save(*args, **kwargs)


class ChatBotCustomDomainDNS(TimestampedModel):
    """ChatBot DNS Records for a ChatBot DNS Host."""

    custom_domain = models.ForeignKey(ChatBotCustomDomain, on_delete=models.CASCADE)
    record_name = models.CharField(max_length=255)
    record_type = models.CharField(max_length=255)
    record_value = models.CharField(max_length=255)
    record_ttl = models.IntegerField(default=600, blank=True, null=True)


class ChatBot(TimestampedModel):
    """A ChatBot API for a customer account."""

    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    subdomain = models.ForeignKey(ChatBotCustomDomainDNS, on_delete=models.CASCADE, blank=True, null=True)
    custom_domain = models.ForeignKey(ChatBotCustomDomain, on_delete=models.CASCADE, blank=True, null=True)
    deployed = models.BooleanField(default=False, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.custom_domain:
            validate = URLValidator()
            try:
                validate("http://" + self.hostname)
            except ValidationError as e:
                raise ValidationError(f"Invalid domain name {self.hostname}") from e
        super().save(*args, **kwargs)

    @property
    def default_host(self):
        return f"{self.name}.{self.account.account_number}.{smarter_settings.customer_api_domain}"

    @property
    def custom_host(self):
        if self.custom_domain and self.custom_domain.is_verified:
            return f"{self.subdomain.record_name}.{self.custom_domain.domain_name}"
        return None

    @property
    def hostname(self):
        return self.custom_host or self.default_host


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
