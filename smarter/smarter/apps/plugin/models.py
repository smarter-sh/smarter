# -*- coding: utf-8 -*-
# pylint: disable=C0114,C0115
"""PluginMeta app models."""
from functools import lru_cache

import yaml
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from taggit.managers import TaggableManager

from smarter.smarter.apps.account.models import Account, UserProfile
from smarter.smarter.common.model_utils import TimestampedModel

from .signals import plugin_selector_history_created


User = get_user_model()


class PluginMeta(TimestampedModel):
    """PluginMeta model."""

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="plugins")
    name = models.CharField(
        help_text="The name of the plugin. Example: 'HR Policy Update' or 'Public Relation Talking Points'.",
        max_length=255,
        default="PluginMeta",
    )
    description = models.TextField(
        help_text="A brief description of the plugin. Be verbose, but not too verbose.",
    )
    version = models.CharField(max_length=255, default="1.0.0")
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="plugins")
    tags = TaggableManager(blank=True)

    def __str__(self):
        return str(self.name) or ""

    # pylint: disable=missing-class-docstring
    class Meta:
        unique_together = (
            "account",
            "name",
        )
        verbose_name = "Plugin"
        verbose_name_plural = "Plugins"


class PluginSelector(TimestampedModel):
    """PluginSelector model."""

    plugin = models.OneToOneField(PluginMeta, on_delete=models.CASCADE, related_name="selector")
    directive = models.CharField(
        help_text="The selection strategy to use for this plugin.", max_length=255, default="search_terms"
    )
    search_terms = models.JSONField(
        help_text="search terms in JSON format that, if detected in the user prompt, will incentivize Smarter to load this plugin.",
        default=list,
    )

    def __str__(self) -> str:
        return str(self.directive) or ""


class PluginSelectorHistory(TimestampedModel):
    """PluginSelectorHistory model."""

    plugin_selector = models.ForeignKey(PluginSelector, on_delete=models.CASCADE, related_name="history")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="plugin_selector_history")
    search_term = models.CharField(max_length=255, blank=True, null=True, default="")
    messages = models.JSONField(help_text="The user prompt messages.", default=list, blank=True, null=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        plugin_selector_history_created.send(sender=self.__class__, plugin_selector_history=self)

    def __str__(self) -> str:
        return str(self.user.username) or ""

    class Meta:
        verbose_name_plural = "Plugin Selector Histories"


class PluginPrompt(TimestampedModel):
    """PluginPrompt model."""

    plugin = models.OneToOneField(PluginMeta, on_delete=models.CASCADE, related_name="prompt")
    system_role = models.TextField(
        help_text="The role of the system in the conversation.",
        null=True,
        blank=True,
        default="You are a helful assistant.",
    )
    model = models.CharField(help_text="The model to use for the completion.", max_length=255, default="gpt-3.5-turbo")
    temperature = models.FloatField(
        help_text="The higher the temperature, the more creative the result.",
        default=0.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    max_tokens = models.IntegerField(
        help_text="The maximum number of tokens for both input and output.",
        default=256,
        validators=[MinValueValidator(0), MaxValueValidator(4096)],
    )

    def __str__(self) -> str:
        return str(self.plugin.name)


class PluginData(TimestampedModel):
    """PluginData model."""

    plugin = models.OneToOneField(PluginMeta, on_delete=models.CASCADE, related_name="plugin_data")
    description = models.TextField(
        help_text="A brief description of what this plugin returns. Be verbose, but not too verbose.",
    )
    return_data = models.JSONField(
        help_text="The JSON data that this plugin returns to OpenAI API when invoked by the user prompt.", default=dict
    )

    @property
    @lru_cache(maxsize=128)
    def return_data_keys(self) -> list:
        """Return all keys in the return_data."""

        def find_keys(data, keys=None):
            if keys is None:
                keys = []
            for key, value in data.items():
                keys.append(key)
                if isinstance(value, dict):
                    find_keys(value, keys)
            return keys

        retval = find_keys(self.return_data)
        return list(retval)

    @property
    def data(self) -> dict:
        return yaml.dump(self.return_data)

    def __str__(self) -> str:
        return str(self.plugin.name)

    class Meta:
        verbose_name = "Plugin Data"
        verbose_name_plural = "Plugin Data"
