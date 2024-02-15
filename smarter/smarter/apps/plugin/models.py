# -*- coding: utf-8 -*-
"""Plugin app models."""
import yaml
from django.contrib.auth import get_user_model
from django.db import models
from taggit.managers import TaggableManager

from smarter.apps.common.model_utils import TimestampedModel


User = get_user_model()


class PluginModel(TimestampedModel):
    """Plugin model."""

    _yaml = models.TextField()

    @property
    def yaml(self):
        return yaml.safe_load(self._yaml)

    @yaml.setter
    def yaml(self, value):
        self._yaml = yaml.safe_dump(value)

    tags = TaggableManager()

    def save(self, *args, **kwargs):
        # Validate YAML data before saving
        yaml.safe_load(self._yaml)
        super().save(*args, **kwargs)
