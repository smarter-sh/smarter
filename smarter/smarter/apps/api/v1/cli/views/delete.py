# pylint: disable=W0613
"""Smarter API command-line interface 'delete' view"""

from .base import CliBaseApiView


class ApiV1CliDeleteApiView(CliBaseApiView):
    """Smarter API command-line interface 'delete' view"""

    def post(self, request):
        return self.broker.delete()
