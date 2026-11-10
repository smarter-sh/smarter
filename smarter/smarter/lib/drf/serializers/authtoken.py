"""The serializer of API keys, :class:`~smarter.lib.drf.models.SmarterAuthToken`, for the web console's list api."""

from rest_framework import serializers

from smarter.apps.account.serializers import (
    MetaDataWithOwnershipModelSerializer,
    UserProfileSerializer,
)
from smarter.lib.drf.manifest.models.auth_token.const import (
    MANIFEST_KIND as AUTH_TOKEN_KIND,
)
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.drf.serializers.camel_case_serializer import (
    SmarterCamelCaseSerializer,
)

# SmarterCamelCaseSerializer is re-exported, for code that imported it from this module.
__all__ = [
    "SmarterAuthTokenSerializer",
    "SmarterCamelCaseSerializer",
]


class SmarterAuthTokenSerializer(MetaDataWithOwnershipModelSerializer):
    """
    Serializer of the SmarterAuthToken model, with its owner's user profile and manifest url.

    A token has no integer id, so ``id`` is its ``key_id``, a string.
    """

    user_profile = UserProfileSerializer()
    # a token has no integer id: it is identified by its key_id, a UUID. DRF lets a subclass
    # replace a declared field with another kind.
    id = serializers.CharField(read_only=True)  # type: ignore[assignment]
    manifest_url = serializers.CharField(read_only=True)

    # pylint: disable=missing-class-docstring
    class Meta(MetaDataWithOwnershipModelSerializer.Meta):
        model = SmarterAuthToken
        kind = AUTH_TOKEN_KIND
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
        ]
        read_only_fields = getattr(MetaDataWithOwnershipModelSerializer.Meta, "read_only_fields", []) + [
            "key_id",
            "hashed_id",
            "last_used_at",
            "ready",
        ]
