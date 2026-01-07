# pylint: disable=W0613
"""Smarter API command-line interface 'apply' view"""

import logging
import platform
import traceback
from http import HTTPStatus

import boto3
from botocore.exceptions import ClientError
from django.http import JsonResponse
from django_redis import get_redis_connection

from smarter.apps.api.v1.cli.views.base import CliBaseApiView
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.lib.journal.enum import (
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
)
from smarter.lib.journal.http import SmarterJournaledJsonResponse


logger = logging.getLogger(__name__)


class ApiV1CliStatusApiView(CliBaseApiView):
    """Smarter API command-line interface 'status' view"""

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the class name in a formatted string
        along with the name of this mixin.
        """
        inherited_class = super().formatted_class_name
        return f"{inherited_class}.ApiV1CliStatusApiView()"

    def get_service_status(self, region_name):
        try:
            client = boto3.client("health", region_name=region_name)
            response = client.describe_events(
                filter={
                    "regions": [
                        region_name,
                    ],
                    "eventStatusCodes": ["open", "upcoming"],
                }
            )
            return response
        except ClientError as e:
            return {"error": str(e)}

    def get_redis_info(self):
        """
        Return Redis server information.
        :return: Redis server information
        :rtype: dict
        """
        logger.debug("%s.get_redis_info() called", self.formatted_class_name)

        client = get_redis_connection("default")
        info = client.info()
        retval = {
            "gcc_version": info.get("gcc_version"),
            "os": info.get("os"),
            "redis_build_id": info.get("redis_build_id"),
            "redis_version": info.get("redis_version"),
        }
        return retval

    def status(self):
        """Get status information about the Smarter platform."""

        logger.debug("%s.status() called", self.formatted_class_name)

        try:
            data = {
                SmarterJournalApiResponseKeys.DATA: {
                    "infrastructures": {
                        "kubernetes": aws_helper.eks.get_kubernetes_info(),
                        "mysql": aws_helper.rds.get_mysql_info(),
                        "redis": self.get_redis_info(),
                    },
                    "compute": {
                        "machine": platform.machine(),
                        "release": platform.release(),
                        "platform": platform.platform(aliased=True),
                        "processor": platform.processor(),
                        "system": platform.system(),
                        "version": platform.version(),
                    },
                },
            }
            return SmarterJournaledJsonResponse(
                self.request,
                command=SmarterJournalCliCommands(SmarterJournalCliCommands.STATUS),
                data=data,
                status=HTTPStatus.OK.value,
            )
        # pylint: disable=W0718
        except Exception as e:
            return JsonResponse(
                data={
                    "error": str(e),
                    "trace": traceback.format_exc(),
                },
                status=HTTPStatus.BAD_REQUEST.value,
            )

    def post(self, request):
        """Get method for PluginManifestView."""
        response = self.status()
        return response
