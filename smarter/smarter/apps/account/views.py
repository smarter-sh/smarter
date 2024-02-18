# -*- coding: utf-8 -*-
# pylint: disable=W0707
"""Account views for smarter api."""
from django.contrib.auth.models import User
from rest_framework import viewsets
from rest_framework.exceptions import NotFound

from .models import Account, PaymentMethodModel, UserProfile
from .serializers import (  # UserProfileSerializer,
    AccountSerializer,
    PaymentMethodSerializer,
    UserSerializer,
)


class AccountViewSet(viewsets.ModelViewSet):
    """Account viewset for smarter api."""

    serializer_class = AccountSerializer

    def get_queryset(self):
        """Override get_queryset to limit to the users for the account."""
        user_profile = UserProfile.objects.get(user=self.request.user)
        return Account.objects.filter(pk=user_profile.account.id)


class UserViewSet(viewsets.ModelViewSet):
    """User profile viewset for smarter api."""

    serializer_class = UserSerializer

    def get_queryset(self):
        """Override get_queryset to limit to the users for the account."""
        user: User = None
        account: Account = None
        user_profile: UserProfile = None

        account_number = self.kwargs.get("account_number")
        username = self.kwargs.get("username")

        print(f"account_number: {account_number}")
        print(f"username: {username}")

        try:
            account = Account.objects.get(account_number=account_number)
        except Account.DoesNotExist:
            raise NotFound("Account not found.")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise NotFound("User not found.")

        try:
            user_profile = UserProfile.objects.get(user=user, account=account)
        except UserProfile.DoesNotExist:
            raise NotFound("User not found in the account.")

        return User.objects.filter(pk=user_profile.user.id)


class UserListViewSet(viewsets.ModelViewSet):
    """User profile viewset for smarter api."""

    serializer_class = UserSerializer

    def get_queryset(self):
        """Override get_queryset to limit to the users for the account."""
        account: Account = None
        account_number = self.kwargs.get("account_number")
        print(f"account_number: {account_number}")

        if not account_number:
            raise NotFound("Account number missing in the URL.")

        try:
            account = Account.objects.get(account_number=account_number)
        except Account.DoesNotExist:
            raise NotFound("Account not found.")

        related_users = UserProfile.objects.filter(account=account)
        return User.objects.filter(id__in=related_users.values("user_id"))


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """Payment method viewset for smarter api."""

    serializer_class = PaymentMethodSerializer

    def get_queryset(self):
        """Override get_queryset to limit to the users for the account."""
        payment_method = self.kwargs.get("payment_method")
        account_number = self.kwargs.get("account_number")
        account = Account.objects.get(account_number=account_number)
        if payment_method:
            return PaymentMethodModel.objects.filter(account=account, name=payment_method)
        return PaymentMethodModel.objects.filter(account=account)


class PaymentMethodListViewSet(viewsets.ModelViewSet):
    """Payment method viewset for smarter api."""

    serializer_class = PaymentMethodSerializer

    def get_queryset(self):
        """Override get_queryset to limit to the users for the account."""
        account_number = self.kwargs.get("account_number")
        account = Account.objects.get(account_number=account_number)
        return PaymentMethodModel.objects.filter(account=account)
