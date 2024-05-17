# pylint: disable=W0613
"""Smarter API command-line interface 'manifest' view"""

from .base import CliBaseApiView


class ApiV1CliManifestApiView(CliBaseApiView):
    """
    Smarter API command-line interface 'manifest' view.
    Returns an example yaml manifest file for the given 'kind'.
    """

    def post(self, request, kind, *args, **kwargs):
        return self.broker.example_manifest(kwargs=kwargs)
