# pylint: disable=W0613
"""Smarter API command-line interface 'apply' view"""

from .base import CliBaseApiView


class ApiV1CliApplyApiView(CliBaseApiView):
    """Smarter API command-line interface 'apply' view"""

    def post(self, request, *args, **kwargs):
        return self.broker.apply(request=request, *args, kwargs=kwargs)
