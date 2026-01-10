"""Account serializers for smarter api"""

import sys
from typing import Optional

from django.http import HttpRequest
from rest_framework import serializers


def is_sphinx_build():
    """Determine if the current execution context is a Sphinx documentation build."""

    return "sphinx" in sys.modules


class SmarterCamelCaseSerializer(serializers.ModelSerializer):
    """Base serializer to convert field names to camelCase."""

    request: Optional[HttpRequest]

    def __init__(self, *args, **kwargs):
        """Initialize the serializer and set the request context."""
        super().__init__(*args, **kwargs)

        # Get the request from the context if available, while
        # guarding against Sphinx autodoc generation issues.
        if is_sphinx_build():
            self.request = None
        else:
            context = getattr(self, "context", None)
            if isinstance(context, dict):
                self.request = context.get("request", None)
            else:
                self.request = None

    def to_representation(self, instance):
        """Convert field names to camelCase."""
        representation = super().to_representation(instance)
        new_representation = {}
        for key, value in representation.items():
            components = key.split("_")
            camel_key = components[0] + "".join(x.title() for x in components[1:])
            new_representation[camel_key] = value
        return new_representation
