# pylint: disable=W0718
"""Smarter API SqlPlugin Manifest handler"""

from rest_framework import serializers

from smarter.apps.account.models import UserProfile
from smarter.apps.plugin.models import PluginMeta
from smarter.lib.drf.serializers import SmarterCamelCaseSerializer
from smarter.lib.manifest.broker import SAMBrokerError


class SAMPluginBrokerError(SAMBrokerError):
    """Base exception for Smarter API Plugin Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Plugin Manifest Broker Error"


class PluginSerializer(SmarterCamelCaseSerializer):
    """Django ORM model serializer for get()"""

    email = serializers.SerializerMethodField()

    def get_email(self, obj: PluginMeta):
        if obj.author:
            user_profile = UserProfile.objects.get(id=obj.author_id)  # type: ignore[union-attr]
            return user_profile.user.email if user_profile.user else None
        return None

    # pylint: disable=C0115
    class Meta:
        model = PluginMeta
        fields = ["name", "plugin_class", "version", "email", "created_at", "updated_at"]


class SAMConnectionBrokerError(SAMBrokerError):
    """Base exception for Smarter API Connection Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Connection Manifest Broker Error"
