"""Account serializers for smarter api"""

import sys
from typing import Optional

from django.http import HttpRequest
from rest_framework import serializers

from smarter.apps.account.serializers import (
    MetaDataWithOwnershipModelSerializer,
    UserProfileSerializer,
)
from smarter.common.utils import to_camel_case, to_snake_case
from smarter.lib import logging
from smarter.lib.drf.models import SmarterAuthToken

logger = logging.getSmarterLogger(__name__)


def is_sphinx_build():
    """Determine if the current execution context is a Sphinx documentation build."""

    return "sphinx" in sys.modules


class SmarterCamelCaseSerializer(serializers.ModelSerializer):
    """Base serializer to convert field names to camelCase."""

    request: Optional[HttpRequest]

    def __init__(self, *args, **kwargs):
        """Initialize the serializer and set the request context."""
        super().__init__(*args, **kwargs)
        self.logger_prefix = logging.formatted_text(__name__ + "." + self.__class__.__name__)

        # Get the request from the context if available, while
        # guarding against Sphinx autodoc generation issues.
        if is_sphinx_build():
            self.request = None
        else:
            context = getattr(self, "context", None)
            if isinstance(context, dict):
                self.request = context.get("request", None)
            else:
                self.request = None

    def to_representation(self, instance):
        """Convert field names to camelCase."""

        representation = super().to_representation(instance)
        new_representation = {}
        for key, value in representation.items():
            # double check that the key is a snake_case string before converting to camelCase
            snake_key = to_snake_case(key)
            camel_key = to_camel_case(snake_key)
            new_representation[camel_key] = value
        return new_representation


class SmarterAuthTokenSerializer(MetaDataWithOwnershipModelSerializer):
    """Serializer for SmarterAuthToken model."""

    user_profile = UserProfileSerializer()

    # pylint: disable=missing-class-docstring
    class Meta(MetaDataWithOwnershipModelSerializer.Meta):
        model = SmarterAuthToken
        fields = [
            "id",
            "hashed_id",
            "key_id",
            "created_at",
            "updated_at",
            "name",
            "user_profile",
            "description",
            "version",
            "annotations",
            "tags",
            "manifest_url",
            "ready",
            "is_active",
            "last_used_at",
            "ready",
        ]
        read_only_fields = getattr(MetaDataWithOwnershipModelSerializer.Meta, "read_only_fields", []) + [
            "key_id",
            "hashed_id",
            "last_used_at",
            "ready",
        ]
