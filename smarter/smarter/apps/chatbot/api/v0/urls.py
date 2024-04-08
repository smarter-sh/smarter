# -*- coding: utf-8 -*-
"""URL configuration for chat app."""

from django.urls import path

from .views.smarter import SmarterChatViewSet


urlpatterns = [
    path("", SmarterChatViewSet.as_view(), name="smarter-chat-api"),
    # TO DO: add paths for langchain, openai and other chatbot providers
]
