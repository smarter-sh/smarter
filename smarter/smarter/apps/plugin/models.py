# -*- coding: utf-8 -*-
"""PluginMeta app models."""
import yaml
from django.contrib.auth import get_user_model
from django.db import models
from taggit.managers import TaggableManager

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.common.model_utils import TimestampedModel


User = get_user_model()


class PluginMeta(TimestampedModel):
    """PluginMeta model."""

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="plugins")
    name = models.CharField(max_length=255, default="PluginMeta")
    description = models.TextField()
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
    directive = models.CharField(max_length=255, default="search_terms")
    search_terms = models.JSONField(default=list)

    def __str__(self) -> str:
        return str(self.directive) or ""


class PluginPrompt(TimestampedModel):
    """PluginPrompt model."""

    plugin = models.OneToOneField(PluginMeta, on_delete=models.CASCADE, related_name="prompt")
    system_role = models.TextField(null=True, blank=True)
    model = models.CharField(max_length=255, default="gpt-3.5-turbo-1106")
    temperature = models.FloatField(default=0.5)
    max_tokens = models.IntegerField(default=256)

    def __str__(self) -> str:
        return str(self.plugin.name)


class PluginData(TimestampedModel):
    """PluginData model."""

    plugin = models.OneToOneField(PluginMeta, on_delete=models.CASCADE, related_name="plugin_data")
    description = models.TextField(null=True, blank=True)
    return_data = models.JSONField(default=dict)

    @property
    def data(self) -> dict:
        return yaml.dump(self.return_data)

    def __str__(self) -> str:
        return str(self.plugin.name)
