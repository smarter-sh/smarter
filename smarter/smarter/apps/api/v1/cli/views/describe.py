# pylint: disable=W0613
"""Smarter API command-line interface 'describe' view"""

from .base import CliBaseApiView


class ApiV1CliDescribeApiView(CliBaseApiView):
    """
    Smarter API command-line interface 'describe' view. Returns the object
    in yaml manifest format.
    """

    def post(self, request, kind: str, name: str):
        return self.broker.describe(request)
