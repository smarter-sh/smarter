# -*- coding: utf-8 -*-
from rest_framework import viewsets

from smarter.apps.api.hello_world.serializers import HelloWorldSerializer

from .models import HelloWorld


class HelloWorldViewSet(viewsets.ModelViewSet):
    queryset = HelloWorld.objects.all()
    serializer_class = HelloWorldSerializer
