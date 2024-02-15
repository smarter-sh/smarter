# -*- coding: utf-8 -*-
"""URLs for all API apps."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from smarter.apps.api.openai_api.views import OpenAIViewSet
from smarter.apps.api.openai_function_calling.views import FunctionCallingViewSet
from smarter.apps.api.openai_langchain.views import LanchainViewSet


router = DefaultRouter()
router.register(r"chatgpt", OpenAIViewSet, basename="chatgpt")
router.register(r"plugins", FunctionCallingViewSet, basename="plugins")
router.register(r"langchain", LanchainViewSet, basename="langchain")

urlpatterns = [
    path("", include(router.urls)),
]
