"""Account serializers for smarter api"""

from typing import Type

from django.contrib.auth import get_user_model
from rest_framework import serializers

from smarter.apps.account.models import (
    Account,
    PaymentMethod,
    SmarterAuthToken,
    UserProfile,
)


User = get_user_model()
UserType = Type[User]


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


class AccountSerializer(serializers.ModelSerializer):
    """Account serializer for smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = Account
        fields = "__all__"


class UserProfileSerializer(serializers.ModelSerializer):
    """User profile serializer for smarter api."""

    user = UserSerializer()
    account = AccountSerializer()

    # pylint: disable=missing-class-docstring
    class Meta:
        model = UserProfile
        fields = "__all__"


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Payment method serializer for smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PaymentMethod
        fields = "__all__"


class SmarterAuthTokenSerializer(serializers.ModelSerializer):
    """API key serializer for smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = SmarterAuthToken
        fields = "__all__"
