# -*- coding: utf-8 -*-
"""Django REST framework serializers for the API admin app."""
from django.contrib.auth.models import User
from rest_framework import serializers


# Serializers define the API representation.
class UserSerializer(serializers.HyperlinkedModelSerializer):
    """Serializer for the User model."""

    class Meta:
        """Meta class for the UserSerializer."""

        model = User
        fields = ["url", "username", "email", "is_staff"]
