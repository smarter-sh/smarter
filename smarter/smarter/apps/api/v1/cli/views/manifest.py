# pylint: disable=W0613
"""Smarter API command-line interface 'manifest' view"""
from http import HTTPStatus

from django.http import JsonResponse

from .base import CliBaseApiView


class CliManifestExampleApiView(CliBaseApiView):
    """
    Smarter API command-line interface 'manifest' view.
    Returns an example yaml manifest file for the given 'kind'.
    """

    def get_manifest(
        self,
    ):
        data = self.broker.example_manifest()
        return JsonResponse(data=data, status=HTTPStatus.OK)

    def post(self, request, kind):
        return self.handler(self.get_manifest)()
