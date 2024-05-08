# pylint: disable=W0613
"""Smarter API command-line interface 'apply' view"""

from .base import CliBaseApiView


class CliDeployApiView(CliBaseApiView):
    """Smarter API command-line interface 'apply' view"""

    def post(self, request):
        return self.handler(self.broker.deploy)()
