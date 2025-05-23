# pylint: disable=W0613
"""Smarter API command-line interface 'apply' view"""

from http import HTTPStatus

from django.http import JsonResponse

from smarter.apps.account.serializers import AccountSerializer
from smarter.common.conf import settings as smarter_settings
from smarter.lib.django.serializers import UserSerializer
from smarter.lib.journal.enum import (
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
)
from smarter.lib.journal.http import SmarterJournaledJsonResponse

from ..base import CliBaseApiView


class ApiV1CliWhoamiApiView(CliBaseApiView):
    """Smarter API command-line interface 'apply' view"""

    def whoami(self):
        try:
            data = {
                SmarterJournalApiResponseKeys.DATA: {
                    "user": UserSerializer(self.user_profile.user).data,
                    "account": AccountSerializer(self.user_profile.account).data,
                    "environment": smarter_settings.environment,
                }
            }
            return SmarterJournaledJsonResponse(
                request=self.request,
                command=SmarterJournalCliCommands(SmarterJournalCliCommands.WHOAMI),
                data=data,
                status=HTTPStatus.OK.value,
            )
        # pylint: disable=W0718
        except Exception as e:
            return JsonResponse(data={"error": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR.value)

    def post(self, request):
        """Get method for PluginManifestView."""
        response = self.whoami()
        return response
