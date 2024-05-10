# pylint: disable=W0613
"""Smarter API command-line interface 'apply' view"""

from http import HTTPStatus

from django.http import JsonResponse

from smarter.apps.account.serializers import AccountSerializer, UserSerializer

from .base import CliBaseApiView


class CliPlatformWhoamiApiView(CliBaseApiView):
    """Smarter API command-line interface 'apply' view"""

    def whoami(self):
        data = {
            "user": UserSerializer(self.user_profile.user).data,
            "account": AccountSerializer(self.user_profile.account).data,
        }
        return JsonResponse(data=data, status=HTTPStatus.OK)

    def post(self, request):
        """Get method for PluginManifestView."""
        return self.handler(self.whoami)()
