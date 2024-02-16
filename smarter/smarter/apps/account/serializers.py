# -*- coding: utf-8 -*-
"""Account serializers for smarter api"""
from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Account, PaymentMethodModel, UserProfile


class UserSerializer(serializers.ModelSerializer):
    """User serializer for smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = User
        fields = ["id", "username", "email"]  # add more fields if needed


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
        fields = ["user", "account"]


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Payment method serializer for smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PaymentMethodModel
        fields = "__all__"
