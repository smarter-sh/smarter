# -*- coding: utf-8 -*-
# pylint: disable=W0613,C0115
"""All models for the OpenAI Function Calling API app."""
import re

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models

from smarter.apps.account.models import Account, APIKey
from smarter.apps.plugin.models import PluginMeta

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
                raise ValidationError("Invalid domain name")
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
            print("AND THE HOSTNAME IS: ", self.hostname)
            if re.match(VALID_DOMAIN_PATTERN, self.hostname) is None:
                raise ValidationError("Invalid domain name")
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


class ChatBotAPIKeys(TimestampedModel):
    """Map of API keys for a ChatBot"""

    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE)
    api_key = models.ForeignKey(APIKey, on_delete=models.CASCADE)


class ChatBotPlugins(TimestampedModel):
    """List of Plugins for a ChatBot"""

    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE)
    plugin = models.ForeignKey(PluginMeta, on_delete=models.CASCADE)


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
