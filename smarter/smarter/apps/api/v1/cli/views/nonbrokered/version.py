# pylint: disable=W0613
"""Smarter API command-line interface 'version' view"""

import platform
from http import HTTPStatus

import requests
from celery import __version__ as celery_version
from django import get_version as get_django_version
from django.http import JsonResponse
from google.generativeai import __version__ as google_genai_version
from Levenshtein import __version__ as levenshtein_version
from openai.version import VERSION as openai_version
from pandas.util._print_versions import show_versions as pandas_version
from pydantic import VERSION as pydantic_version
from rest_framework import __version__ as rest_framework_version

from smarter.apps.api.signals import api_request_completed
from smarter.apps.api.v1.cli.views.base import APIV1CLIViewError, CliBaseApiView
from smarter.common.conf import settings as smarter_settings
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.lib.journal.enum import (
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
)
from smarter.lib.journal.http import SmarterJournaledJsonResponse


class ApiV1CliVersionApiView(CliBaseApiView):
    """Smarter API command-line interface 'version' view"""

    def cli_version(self):
        """
        retrieve the version of the smarter-cli by reading the version file
        from the smarter-cli package
        """
        url = "https://raw.githubusercontent.com/smarter-sh/smarter-cli/main/VERSION"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            version = response.text.strip()
            return version
        raise APIV1CLIViewError(f"Failed to get version from {url}. HTTP status code: {response.status_code}")

    def info(self):
        try:
            data = {
                SmarterJournalApiResponseKeys.DATA: {
                    "api": {
                        "version": smarter_settings.version,
                        "python": {
                            "botocore": aws_helper.aws.version,
                            "celery": celery_version,
                            "django": get_django_version(),
                            "levenshtein": levenshtein_version,
                            "google_genai": google_genai_version,
                            "llamaai": "unknown",
                            "openai": openai_version,
                            "pandas": pandas_version(),
                            "pydantic": pydantic_version,
                            "python": platform.python_version(),
                            "rest_framework": rest_framework_version,
                        },
                    },
                    "cli": {
                        "version": self.cli_version(),
                    },
                }
            }

            return SmarterJournaledJsonResponse(
                request=self.request,
                command=SmarterJournalCliCommands(SmarterJournalCliCommands.VERSION),
                data=data,
                status=HTTPStatus.OK.value,
            )
        # pylint: disable=W0718
        except Exception as e:
            return JsonResponse(data={"error": str(e)}, status=HTTPStatus.BAD_REQUEST.value)

    def post(self, request):
        response = self.info()
        api_request_completed.send(sender=self.__class__, instance=self, request=request, response=response)
        return response
