# -*- coding: utf-8 -*-
"""Account urls for smarter api"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from smarter.apps.account.views import (
    AccountViewSet,
    PaymentMethodListViewSet,
    PaymentMethodViewSet,
    UserListViewSet,
    UserViewSet,
)


# Routers provide an easy way of automatically determining the URL conf.
router = DefaultRouter()
router.register(r"(?P<account_number>[\d-]+)", AccountViewSet, basename="account")
router.register(r"(?P<account_number>[\d-]+)/users/(?P<username>[\w.@+-]+)", UserViewSet, basename="user")
router.register(r"(?P<account_number>[\d-]+)/users", UserListViewSet, basename="users")

router.register(
    r"(?P<account_number>[\d-]+)/payment-methods/(?P<payment_method>[\w.@+-]+)",
    PaymentMethodViewSet,
    basename="payment-methods",
)
router.register(r"(?P<account_number>[\d-]+)/payment-methods", PaymentMethodListViewSet, basename="payment-methods")

urlpatterns = [
    path("account/", include(router.urls)),
]
