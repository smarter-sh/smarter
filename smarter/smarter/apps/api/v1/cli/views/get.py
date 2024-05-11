# pylint: disable=W0613
"""Smarter API command-line interface 'get' view"""


from .base import CliBaseApiView


class ApiV1CliGetApiView(CliBaseApiView):
    """Smarter API command-line interface 'get' view"""

    def post(self, request):
        return self.broker.get(request)
