"""
Serializer classes for the Provider app.
"""

from smarter.apps.account.serializers import (
    AccountMiniSerializer,
    SecretSerializer,
    UserMiniSerializer,
)
from smarter.lib.drf.serializers import SmarterCamelCaseSerializer

from .models import (
    Provider,
    ProviderModel,
    ProviderModelVerification,
    ProviderVerification,
)


class ProviderSerializer(SmarterCamelCaseSerializer):
    """PluginMeta model serializer."""

    owner = UserMiniSerializer(read_only=True)
    account = AccountMiniSerializer(read_only=True)
    api_key = SecretSerializer(read_only=True)

    # pylint: disable=missing-class-docstring
    class Meta:
        model = Provider
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "owner", "account"]


class ProviderModelSerializer(SmarterCamelCaseSerializer):
    """ProviderModel model serializer."""

    provider = ProviderSerializer(read_only=True)

    # pylint: disable=missing-class-docstring
    class Meta:
        model = ProviderModel
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "provider"]


class ProviderVerificationSerializer(SmarterCamelCaseSerializer):
    """ProviderVerification model serializer."""

    provider = ProviderSerializer(read_only=True)

    # pylint: disable=missing-class-docstring
    class Meta:
        model = ProviderVerification
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "provider"]


class ProviderModelVerificationSerializer(SmarterCamelCaseSerializer):
    """ProviderModelVerification model serializer."""

    provider_model = ProviderModelSerializer(read_only=True)

    # pylint: disable=missing-class-docstring
    class Meta:
        model = ProviderModelVerification
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "provider_model"]
