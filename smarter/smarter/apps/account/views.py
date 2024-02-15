# -*- coding: utf-8 -*-
"""Account views for smarter api."""
from rest_framework import viewsets

from .models import Account, PaymentMethodModel, UserProfile
from .serializers import (
    AccountSerializer,
    PaymentMethodSerializer,
    UserProfileSerializer,
)


class AccountViewSet(viewsets.ModelViewSet):
    """Account viewset for smarter api."""

    serializer_class = AccountSerializer

    def get_queryset(self):
        """Override get_queryset to limit to the users for the account."""
        return Account.objects.filter(account=self.request.user.account)


class UserProfileViewSet(viewsets.ModelViewSet):
    """User profile viewset for smarter api."""

    serializer_class = UserProfileSerializer

    def get_queryset(self):
        """Override get_queryset to limit to the users for the account."""
        return UserProfile.objects.filter(account=self.request.user.account)


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """Payment method viewset for smarter api."""

    serializer_class = PaymentMethodSerializer

    def get_queryset(self):
        """Override get_queryset to limit to the users for the account."""
        return PaymentMethodModel.objects.filter(account=self.request.user.account)
