# -*- coding: utf-8 -*-
"""URLs for all API apps."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from smarter.apps.api.openai_api.views import OpenAIViewSet
from smarter.apps.api.openai_function_calling.views import FunctionCallingViewSet
from smarter.apps.api.openai_langchain.views import LanchainViewSet


router = DefaultRouter()
router.register(r"chat/chatgpt", OpenAIViewSet, basename="chatgpt")
router.register(r"chat", FunctionCallingViewSet, basename="chat")
router.register(r"chat/langchain", LanchainViewSet, basename="langchain")

urlpatterns = [
    path("", include(router.urls)),
]
