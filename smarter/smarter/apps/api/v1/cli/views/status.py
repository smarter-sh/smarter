# pylint: disable=W0613
"""Smarter API command-line interface 'apply' view"""

import platform
from http import HTTPStatus

import boto3
from botocore.exceptions import ClientError
from django.http import JsonResponse
from django_redis import get_redis_connection

from smarter.common.helpers.aws_helpers import aws_helper
from smarter.lib.journal.enum import SmarterJournalCliCommands, SmarterJournalThings
from smarter.lib.journal.http import SmarterJournaledJsonResponse

from .base import CliBaseApiView


class ApiV1CliStatusApiView(CliBaseApiView):
    """Smarter API command-line interface 'apply' view"""

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
        try:
            data = {
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
            }
            return SmarterJournaledJsonResponse(
                self.request,
                command=SmarterJournalCliCommands(SmarterJournalCliCommands.STATUS),
                thing=SmarterJournalThings(),
                data=data,
                status=HTTPStatus.OK,
            )
        # pylint: disable=W0718
        except Exception as e:
            return JsonResponse(data={"error": str(e)}, status=HTTPStatus.BAD_REQUEST)

    def post(self, request):
        """Get method for PluginManifestView."""
        return self.status()
