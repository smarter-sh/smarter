# -*- coding: utf-8 -*-
"""Account views for smarter api."""
from rest_framework import viewsets

from .models import AccountModel, PaymentMethodModel, UserProfile
from .serializers import (
    AccountSerializer,
    PaymentMethodSerializer,
    UserProfileSerializer,
)


class AccountViewSet(viewsets.ModelViewSet):
    """Account viewset for smarter api."""

    queryset = AccountModel.objects.all()
    serializer_class = AccountSerializer


class UserProfileViewSet(viewsets.ModelViewSet):
    """User profile viewset for smarter api."""

    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """Payment method viewset for smarter api."""

    queryset = PaymentMethodModel.objects.all()
    serializer_class = PaymentMethodSerializer
