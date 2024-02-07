from django.contrib.auth.models import User
from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from .models import HelloWorld
from smarter.apps.api.hello_world.serializers import HelloWorldSerializer, UserSerializer

from rest_framework import serializers, viewsets


# ViewSets define the view behavior.
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class HelloWorldViewSet(viewsets.ModelViewSet):
    queryset = HelloWorld.objects.all()
    serializer_class = HelloWorldSerializer
