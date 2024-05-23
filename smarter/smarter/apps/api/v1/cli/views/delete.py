# pylint: disable=W0613
"""Smarter API command-line interface 'delete' view"""

from .base import CliBaseApiView


class ApiV1CliDeleteApiView(CliBaseApiView):
    """Smarter API command-line interface 'delete' view"""

    def post(self, request, kind: str, *args, **kwargs):
        return self.broker.delete(request=request, *args, kwargs=kwargs)
