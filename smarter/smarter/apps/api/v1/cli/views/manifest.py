# pylint: disable=W0613
"""Smarter API command-line interface 'manifest' view"""

from .base import CliBaseApiView


class CliManifestExampleApiView(CliBaseApiView):
    """
    Smarter API command-line interface 'manifest' view.
    Returns an example yaml manifest file for the given 'kind'.
    """

    def post(self, request):
        return self.handler(self.broker.example_manifest)()
