# pylint: disable=W0613
"""Smarter API command-line interface 'apply' view"""

from http import HTTPStatus

from django.http import JsonResponse

from smarter.apps.account.serializers import AccountSerializer
from smarter.lib.django.serializers import UserSerializer

from .base import CliBaseApiView


class ApiV1CliWhoamiApiView(CliBaseApiView):
    """Smarter API command-line interface 'apply' view"""

    def whoami(self):
        try:
            data = {
                "user": UserSerializer(self.user_profile.user).data,
                "account": AccountSerializer(self.user_profile.account).data,
            }
            return JsonResponse(data=data, status=HTTPStatus.OK)
        # pylint: disable=W0718
        except Exception as e:
            return JsonResponse(data={"error": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def post(self, request):
        """Get method for PluginManifestView."""
        return self.whoami()
