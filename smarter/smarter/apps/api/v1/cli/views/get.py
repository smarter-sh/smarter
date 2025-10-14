# pylint: disable=W0613
"""Smarter API command-line interface 'get' view"""

import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from smarter.common.conf import settings as smarter_settings
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .base import CliBaseApiView
from .const import (
    COMMON_SWAGGER_PARAMETERS,
    COMMON_SWAGGER_RESPONSES,
    EXAMPLE_GET_RESPONSE,
)


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class ApiV1CliGetApiView(CliBaseApiView):
    """
    This is the API endpoint for the 'get' command in the Smarter command-line interface (CLI).

    The 'get' command is a Smarter Brokered and Journaled operation that is used with all Smarter resources. Get criteria is passed as url query parameters.

    The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

    The response from this endpoint is a JSON list object.

    This class is a child of the Django Rest Framework View.
    """

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the class name in a formatted string
        along with the name of this mixin.
        """
        inherited_class = super().formatted_class_name
        return f"{inherited_class}.ApiV1CliGetApiView()"

    @swagger_auto_schema(
        operation_description="""
Executes the 'get' command for Smarter resources using a YAML manifest in the smarter.sh/v1 format.

This is the API endpoint for the 'get' command in the Smarter command-line interface (CLI). The 'get' command is a Smarter Brokered and Journaled operation that is used with all Smarter resources. Get criteria is passed as url query parameters.

The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

The response from this endpoint is a JSON object.

This is a brokered operation, so the actual work is delegated to the appropriate broker based on the resource kind specified in the manifest. See smarter.apps.api.v1.cli.brokers.Brokers
""",
        responses={
            **COMMON_SWAGGER_RESPONSES,
            200: openapi.Response(
                description="Got resources successfully",
                examples=EXAMPLE_GET_RESPONSE,
            ),
        },
        manual_parameters=[COMMON_SWAGGER_PARAMETERS["kind"]],
    )
    def post(self, request, kind: str, *args, **kwargs):
        logger.info("%s.post() %s", self.formatted_class_name, kwargs)
        response = self.broker.get(request=request, kwargs=kwargs)
        return response
