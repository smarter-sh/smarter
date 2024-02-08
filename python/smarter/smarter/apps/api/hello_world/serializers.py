# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from rest_framework import serializers

from .models import HelloWorld


class HelloWorldSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelloWorld
        fields = "__all__"


# Serializers define the API representation.
class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ["url", "username", "email", "is_staff"]
