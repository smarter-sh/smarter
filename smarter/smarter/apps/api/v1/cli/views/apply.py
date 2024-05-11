# pylint: disable=W0613
"""Smarter API command-line interface 'apply' view"""

from .base import CliBaseApiView


class CliApplyManifestApiView(CliBaseApiView):
    """Smarter API command-line interface 'apply' view"""

    def post(self, request):
        return self.broker.apply()
