# -*- coding: utf-8 -*-
"""URL configuration for chat app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from smarter.apps.langchain_passthrough.views import LanchainViewSet
from smarter.apps.openai_passthrough.views import OpenAIViewSet

from .views.chat import FunctionCallingViewSet


# Routers provide an easy way of automatically determining the URL conf.
router = DefaultRouter()

router.register(r"", FunctionCallingViewSet, basename="chat")
router.register(r"chatgpt", OpenAIViewSet, basename="chatgpt")
router.register(r"langchain", LanchainViewSet, basename="langchain")

urlpatterns = [
    path("", include(router.urls)),
]
