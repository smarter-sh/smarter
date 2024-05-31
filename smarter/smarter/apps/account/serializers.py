"""Account serializers for smarter api"""

from rest_framework import serializers

from smarter.apps.account.models import Account, PaymentMethod, UserProfile
from smarter.lib.django.serializers import UserMiniSerializer


class AccountSerializer(serializers.ModelSerializer):
    """Account serializer for smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = Account
        fields = "__all__"


class AccountMiniSerializer(serializers.ModelSerializer):
    """Account serializer for smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = Account
        fields = ("account_number",)


class UserProfileSerializer(serializers.ModelSerializer):
    """User profile serializer for smarter api."""

    user = UserMiniSerializer()
    account = AccountMiniSerializer()

    # pylint: disable=missing-class-docstring
    class Meta:
        model = UserProfile
        fields = ["user", "account"]


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Payment method serializer for smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PaymentMethod
        fields = "__all__"
