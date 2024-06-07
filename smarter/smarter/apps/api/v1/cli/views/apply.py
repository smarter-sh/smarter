# pylint: disable=W0613
"""Smarter API command-line interface 'apply' view"""

from drf_yasg.utils import swagger_auto_schema

from .base import CliBaseApiView


class ApiV1CliApplyApiView(CliBaseApiView):
    """Smarter API command-line interface 'apply' view"""

    @swagger_auto_schema(operation_description="POST description")
    def post(self, request, *args, **kwargs):
        """POST method for the 'apply' view."""
        return self.broker.apply(request=request, kwargs=kwargs)
