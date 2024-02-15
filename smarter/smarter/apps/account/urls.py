# -*- coding: utf-8 -*-
"""Account urls for smarter api"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from smarter.apps.account.views import AccountViewSet, PaymentMethodViewSet
from smarter.apps.api.views.views import UserViewSet


# Routers provide an easy way of automatically determining the URL conf.
router = DefaultRouter()
router.register(r"", AccountViewSet, basename="account")
router.register(r"users", UserViewSet, basename="users")
router.register(r"payment-methods", PaymentMethodViewSet, basename="payment-methods")

urlpatterns = [
    path("account", include(router.urls)),
]
