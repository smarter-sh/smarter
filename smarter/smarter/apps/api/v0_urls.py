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

from smarter.apps.api.views.views import LogoutView
from smarter.apps.openai_api.views import OpenAIViewSet
from smarter.apps.openai_function_calling.views import FunctionCallingViewSet
from smarter.apps.openai_langchain.views import LanchainViewSet


# Routers provide an easy way of automatically determining the URL conf.
router = DefaultRouter()

router.register(r"chat", FunctionCallingViewSet, basename="chat")
router.register(r"chat/chatgpt", OpenAIViewSet, basename="chatgpt")
router.register(r"chat/langchain", LanchainViewSet, basename="langchain")

urlpatterns = [
    path("", include(router.urls)),
    path("api-auth/logout/", LogoutView.as_view(), name="logout"),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
]
