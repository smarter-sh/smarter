# pylint: disable=W0613
"""Smarter API command-line interface 'apply' view"""

from http import HTTPStatus

import boto3
from botocore.exceptions import ClientError
from django.http import JsonResponse

from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterExceptionBase, error_response_factory

from .base import CliBaseApiView


class CliPlatformStatusApiView(CliBaseApiView):
    """Smarter API command-line interface 'apply' view"""

    def get_eks_status(self, cluster_name):
        try:
            client = boto3.client("eks", region_name=smarter_settings.aws_region)
            response = client.describe_cluster(name=cluster_name)
            return response["cluster"]["status"]
        except ClientError as e:
            return {"error": str(e)}

    def get_rds_status(self, db_instance_identifier):
        try:
            client = boto3.client("rds", region_name=smarter_settings.aws_region)
            response = client.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
            return response["DBInstances"][0]["DBInstanceStatus"]
        except ClientError as e:
            return {"error": str(e)}

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

    def post(self, request):
        """Get method for PluginManifestView."""
        try:
            data = {
                "infrastructure": {
                    "eks": self.get_eks_status(smarter_settings.aws_eks_cluster_name),
                    "mysql": self.get_rds_status(smarter_settings.aws_eks_cluster_name),
                    "aws": {
                        "region": smarter_settings.aws_region,
                        "status": self.get_service_status(smarter_settings.aws_region),
                    },
                },
            }

            return JsonResponse(data=data, status=HTTPStatus.OK)
        except NotImplementedError as e:
            return JsonResponse(error_response_factory(e=e), status=HTTPStatus.NOT_IMPLEMENTED)
        except SmarterExceptionBase as e:
            return JsonResponse(error_response_factory(e=e), status=HTTPStatus.BAD_REQUEST)
        # pylint: disable=W0718
        except Exception as e:
            return JsonResponse(error_response_factory(e=e), status=HTTPStatus.INTERNAL_SERVER_ERROR)
