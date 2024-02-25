# -*- coding: utf-8 -*-
"""
URL configuration for smarter project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from smarter.apps.api.views.views import custom_api_root_v0
from smarter.apps.chat.views import FunctionCallingViewSet
from smarter.apps.langchain_passthrough.views import LanchainViewSet
from smarter.apps.openai_passthrough.views import OpenAIViewSet


# Routers provide an easy way of automatically determining the URL conf.
router = DefaultRouter()

router.register(r"chat", FunctionCallingViewSet, basename="chat")
router.register(r"chat/chatgpt", OpenAIViewSet, basename="chatgpt")
router.register(r"chat/langchain", LanchainViewSet, basename="langchain")

urlpatterns = [
    path("", custom_api_root_v0, name="custom_api_root_v0"),
    path("", include(router.urls)),
    path("", include("smarter.apps.account.v0_urls")),
    path("", include("smarter.apps.plugin.v0_urls")),
]
