# -*- coding: utf-8 -*-
"""URLs for all API apps."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from smarter.apps.api.hello_world.views import HelloWorldViewSet
from smarter.apps.api.openai_api.views import OpenAIViewSet
from smarter.apps.api.openai_function_calling.views import FunctionCallingViewSet
from smarter.apps.api.openai_langchain.views import LanchainViewSet


router = DefaultRouter()
router.register(r"hello_world", HelloWorldViewSet, basename="hello_world")
router.register(r"openai", OpenAIViewSet, basename="openai")
router.register(r"function-calling", FunctionCallingViewSet, basename="function-calling")
router.register(r"langchain", FunctionCallingViewSet, basename="langchain")

urlpatterns = [
    path("", include(router.urls)),
]
