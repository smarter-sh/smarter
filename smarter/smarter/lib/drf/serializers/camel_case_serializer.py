"""The base serializer of Smarter apis whose json keys are camelCase."""

import sys
from typing import Optional

from django.http import HttpRequest
from rest_framework import serializers

from smarter.common.utils import to_camel_case, to_snake_case
from smarter.lib import logging

logger = logging.getSmarterLogger(__name__)


def is_sphinx_build() -> bool:
    """
    Return whether the code runs in a Sphinx documentation build.

    :returns: True if the ``sphinx`` module is imported.
    """
    return "sphinx" in sys.modules


class SmarterCamelCaseSerializer(serializers.ModelSerializer):
    """Base serializer to convert field names to camelCase."""

    request: Optional[HttpRequest]

    def __init__(self, *args, **kwargs):
        """
        Initialize the serializer, and set ``request`` from the serializer's context.

        :param args: Passed to DRF's ``ModelSerializer``.
        :param kwargs: Passed to DRF's ``ModelSerializer``.
        """
        super().__init__(*args, **kwargs)
        self.logger_prefix = logging.SmarterFormattedText.text(__name__ + "." + self.__class__.__name__)

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
        """
        Serialize an instance, with its field names in camelCase.

        :param instance: The model instance.
        :returns: The serialized instance, with camelCase keys.
        """
        representation = super().to_representation(instance)
        new_representation = {}
        for key, value in representation.items():
            # double check that the key is a snake_case string before converting to camelCase
            snake_key = to_snake_case(key)
            camel_key = to_camel_case(snake_key)
            new_representation[camel_key] = value
        return new_representation
