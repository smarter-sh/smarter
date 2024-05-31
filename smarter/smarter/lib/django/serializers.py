"""Django serializer helpers for smarter api."""

from rest_framework import serializers

from .user import User


class UserSerializer(serializers.ModelSerializer):
    """User serializer for smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_staff",
            "is_superuser",
        ]  # add more fields if needed


class UserMiniSerializer(serializers.ModelSerializer):
    """User serializer for smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = User
        fields = [
            "username",
            "email",
        ]  # add more fields if needed
