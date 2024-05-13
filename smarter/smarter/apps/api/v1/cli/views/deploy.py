# pylint: disable=W0613
"""Smarter API command-line interface 'deploy' view"""

from .base import CliBaseApiView


class ApiV1CliDeployApiView(CliBaseApiView):
    """Smarter API command-line interface 'deploy' view"""

    def post(self, request, kind: str, name: str):
        return self.broker.deploy(request)
