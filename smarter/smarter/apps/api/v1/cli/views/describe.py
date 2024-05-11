# pylint: disable=W0613
"""Smarter API command-line interface 'describe' view"""

from .base import CliBaseApiView


class CliDescribeApiView(CliBaseApiView):
    """
    Smarter API command-line interface 'describe' view. Returns the object
    in yaml manifest format.
    """

    def post(self, request):
        return self.handler(self.broker.describe)()
