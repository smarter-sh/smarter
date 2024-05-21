# pylint: disable=W0613
"""Smarter API command-line interface 'version' view"""

import platform
from http import HTTPStatus
from subprocess import check_output

from celery import __version__ as celery_version
from django import get_version as get_django_version
from django.http import JsonResponse
from django_redis import get_redis_connection
from langchain import __version__ as langchain_version
from Levenshtein import __version__ as levenshtein_version
from openai.version import VERSION as openai_version
from pandas.util._print_versions import show_versions as pandas_version
from pydantic import VERSION as pydantic_version
from rest_framework import __version__ as rest_framework_version

from smarter.common.conf import settings as smarter_settings
from smarter.common.helpers.aws_helpers import aws_helper

from .base import CliBaseApiView


class ApiV1CliVersionApiView(CliBaseApiView):
    """Smarter API command-line interface 'version' view"""

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

    def info(self):
        try:
            data = {
                "smarter": smarter_settings.version,
                "python": {
                    "botocore": aws_helper.aws.version,
                    "celery": celery_version,
                    "django": get_django_version(),
                    "langchain": langchain_version,
                    "levenshtein": levenshtein_version,
                    "openai": openai_version,
                    "pandas": pandas_version(),
                    "pydantic": pydantic_version,
                    "python": platform.python_version(),
                    "rest_framework": rest_framework_version,
                },
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

            return JsonResponse(data=data, status=HTTPStatus.OK)
        # pylint: disable=W0718
        except Exception as e:
            return JsonResponse(data={"error": str(e)}, status=HTTPStatus.BAD_REQUEST)

    def post(self, request):
        return self.info()
