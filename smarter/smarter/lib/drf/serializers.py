"""Account serializers for smarter api"""

from django.core.handlers.wsgi import WSGIRequest
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


class SmarterCamelCaseSerializer(serializers.ModelSerializer):
    """Base serializer to convert field names to camelCase."""

    request: WSGIRequest

    def __init__(self, *args, **kwargs):
        """Initialize the serializer and set the request context."""
        super().__init__(*args, **kwargs)
        self.request = self.context.get("request", None)

    def to_representation(self, instance):
        """Convert field names to camelCase."""
        representation = super().to_representation(instance)
        new_representation = {}
        for key, value in representation.items():
            components = key.split("_")
            camel_key = components[0] + "".join(x.title() for x in components[1:])
            new_representation[camel_key] = value
        return new_representation
