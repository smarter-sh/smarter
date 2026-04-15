# pylint: disable=C0115
"""
Serializer classes for the Vectorstore app.
"""

from smarter.apps.account.models import User, UserProfile
from smarter.apps.account.serializers import (
    AccountMiniSerializer,
    MetaDataWithOwnershipModelSerializer,
    SecretSerializer,
    UserMiniSerializer,
)
from smarter.apps.provider.serializers import (
    ProviderModelSerializer,
    ProviderSerializer,
)

from .models import VectorestoreMeta


class VectorstoreSerializer(MetaDataWithOwnershipModelSerializer):
    """PluginMeta model serializer."""

    owner = UserMiniSerializer(read_only=True)
    account = AccountMiniSerializer(read_only=True)
    password = SecretSerializer(read_only=True)
    provider = ProviderSerializer(read_only=True)
    provider_model = ProviderModelSerializer(read_only=True)

    class Meta:
        model = VectorestoreMeta
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "owner", "account"]

    def get_queryset(self):
        name = self.request.GET.get("name")  # type: ignore
        backend = self.request.GET.get("backend")  # type: ignore
        user = self.request.user if hasattr(self.request, "user") else None  # type: ignore
        if name and isinstance(user, User) and user.is_authenticated:
            user_profile = UserProfile.get_cached_object(user=user)
            return VectorestoreMeta.get_cached_object(name=name, user_profile=user_profile, backend=backend)
        return VectorestoreMeta.objects.none()
