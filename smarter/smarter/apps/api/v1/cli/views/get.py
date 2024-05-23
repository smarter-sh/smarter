# pylint: disable=W0613
"""Smarter API command-line interface 'get' view"""
from .base import CliBaseApiView


class ApiV1CliGetApiView(CliBaseApiView):
    """Smarter API command-line interface 'get' view"""

    def post(self, request, kind: str, *args, **kwargs):
        """
        post() for 'get' view. Valid urls params:
        'all': boolean = False
        'tags': comma-delimited str = None
        """
        return self.broker.get(request, args=args, kwargs=kwargs)
