# pylint: disable=W0613
"""Smarter API command-line interface 'apply' view"""

from .base import CliBaseApiView


class ApiV1CliLogsApiView(CliBaseApiView):
    """Smarter API command-line interface 'apply' view"""

    def post(self, request, kind, *args, **kwargs):
        return self.broker.logs(request=request, kwargs=kwargs)
