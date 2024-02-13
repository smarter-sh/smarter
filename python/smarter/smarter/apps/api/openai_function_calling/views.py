# -*- coding: utf-8 -*-
"""All Django views for the OpenAI Function Calling API app."""
from rest_framework import permissions, viewsets
from rest_framework.response import Response


class FunctionCallingViewSet(viewsets.ViewSet):
    """top-level viewset for openai api function calling"""

    permission_classes = [permissions.AllowAny]  # change this line

    # pylint: disable=W0613
    def list(self, request):
        """override the list method to return a custom JSON response."""
        return Response({"key": "function calling response"})
