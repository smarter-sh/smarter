"""Account serializers for smarter api"""

from rest_framework import serializers

from .models import SmarterAuthToken


class SmarterAuthTokenSerializer(serializers.ModelSerializer):
    """API key serializer for smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = SmarterAuthToken
        fields = "__all__"
