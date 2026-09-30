# pylint: disable=C0115
"""Serializer classes for the Vectorstore app."""

from django.urls import reverse
from rest_framework import serializers

from smarter.apps.account.models import User, UserProfile
from smarter.apps.account.serializers import (
    AccountMiniSerializer,
    MetaDataWithOwnershipModelSerializer,
    UserMiniSerializer,
)
from smarter.apps.provider.serializers import (
    ProviderModelSerializer,
    ProviderSerializer,
)
from smarter.apps.secret.serializers import SecretSerializer

from .models import VectorstoreMeta


class VectorstoreSerializer(MetaDataWithOwnershipModelSerializer):
    """PluginMeta model serializer."""

    owner = UserMiniSerializer(read_only=True)
    account = AccountMiniSerializer(read_only=True)
    password = SecretSerializer(read_only=True)
    provider = ProviderSerializer(read_only=True)
    provider_model = ProviderModelSerializer(read_only=True)

    manifest_url = serializers.SerializerMethodField()

    class Meta:
        model = VectorstoreMeta
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "owner", "account"]

    def get_queryset(self):
        name = self.request.GET.get("name")  # type: ignore
        backend = self.request.GET.get("backend")  # type: ignore
        user = self.request.user if hasattr(self.request, "user") else None  # type: ignore
        if name and isinstance(user, User) and user.is_authenticated:
            user_profile = UserProfile.get_cached_object(user=user)
            return VectorstoreMeta.get_cached_object(name=name, user_profile=user_profile, backend=backend)
        return VectorstoreMeta.objects.none()

    def get_manifest_url(self, obj: VectorstoreMeta) -> str:
        """The URL of the VectorstoreMeta's detail view, which renders its manifest."""
        # pylint: disable=C0415
        from .urls import VectorstoreReverseNames

        return reverse(
            f"{VectorstoreReverseNames.namespace}:{VectorstoreReverseNames.detailview}",
            kwargs={"hashed_id": obj.hashed_id},
        )
