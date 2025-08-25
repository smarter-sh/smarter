"""Account serializers for smarter api"""

from typing import Optional

from django.http import HttpRequest
from rest_framework import serializers


class SmarterCamelCaseSerializer(serializers.ModelSerializer):
    """Base serializer to convert field names to camelCase."""

    request: Optional[HttpRequest]

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
