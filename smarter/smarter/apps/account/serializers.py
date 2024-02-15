# -*- coding: utf-8 -*-
"""Account serializers for smarter api"""
from rest_framework import serializers

from .models import Account, PaymentMethodModel, UserProfile


class AccountSerializer(serializers.ModelSerializer):
    """Account serializer for smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = Account
        fields = "__all__"


class UserProfileSerializer(serializers.ModelSerializer):
    """User profile serializer for smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = UserProfile
        fields = "__all__"


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Payment method serializer for smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PaymentMethodModel
        fields = "__all__"
