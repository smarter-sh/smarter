"""Account serializers for smarter api"""

from rest_framework import serializers

from smarter.lib.django.serializers import UserMiniSerializer

from .models import SmarterAuthToken


class SmarterAuthTokenSerializer(serializers.ModelSerializer):
    """API key serializer for smarter api."""

    user = UserMiniSerializer(read_only=True)

    # pylint: disable=missing-class-docstring
    class Meta:
        model = SmarterAuthToken
        fields = [
            "digest",
            "token_key",
            "user",
            "created",
            "expiry",
            "key_id",
            "name",
            "description",
            "last_used_at",
            "is_active",
        ]
