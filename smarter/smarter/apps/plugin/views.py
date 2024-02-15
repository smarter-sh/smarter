# -*- coding: utf-8 -*-
"""Plugin views."""
from rest_framework import viewsets

from .models import Plugin
from .serializers import PluginModelSerializer


class PluginModelViewSet(viewsets.ModelViewSet):
    """Plugin model view set."""

    queryset = Plugin.objects.all()
    serializer_class = PluginModelSerializer
