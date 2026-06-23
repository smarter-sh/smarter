# pylint: disable=W0718
"""Smarter API SqlProxy Manifest handler."""

from rest_framework import serializers

from smarter.apps.account.models import UserProfile
from smarter.apps.proxy.models import Proxy
from smarter.lib.drf.serializers import SmarterCamelCaseSerializer
from smarter.lib.manifest.broker import SAMBrokerError


class SAMProxyBrokerError(SAMBrokerError):
    """Base exception for Smarter API Proxy Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Proxy Manifest Broker Error"


class ProxySerializer(SmarterCamelCaseSerializer):
    """Django ORM model serializer for get()."""

    email = serializers.SerializerMethodField()

    def get_email(self, obj: Proxy):
        if obj.user_profile:
            user_profile = UserProfile.objects.get(id=obj.user_profile_id)  # type: ignore[union-attr]
            return user_profile.cached_user.email if user_profile.cached_user else None
        return None

    # pylint: disable=C0115
    class Meta:
        model = Proxy
        fields = ["name", "plugin_class", "version", "email", "created_at", "updated_at"]
