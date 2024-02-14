# -*- coding: utf-8 -*-
"""Django REST framework views for the API admin app."""
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from smarter.apps.api.api_admin.serializers import UserSerializer


# ViewSets define the view behavior.
# pylint: disable=too-many-ancestors
class UserViewSet(viewsets.ModelViewSet):
    """Viewset for the User model."""

    queryset = User.objects.all()
    serializer_class = UserSerializer


class LogoutView(APIView):
    """View for logging out browser session."""

    permission_classes = [AllowAny]

    def get(self, request):
        """Log out the user."""
        logout(request)
        return Response({"detail": "Logged out"})
