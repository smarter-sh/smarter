# -*- coding: utf-8 -*-
"""Account serializers for smarter api"""
from django.contrib.auth import get_user_model
from rest_framework import serializers

from ...models import Account, PaymentMethod, UserProfile


User = get_user_model()


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
