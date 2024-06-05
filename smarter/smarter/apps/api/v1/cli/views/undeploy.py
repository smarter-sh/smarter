# pylint: disable=W0613
"""Smarter API command-line interface 'deploy' view"""

from .base import CliBaseApiView


class ApiV1CliUndeployApiView(CliBaseApiView):
    """Smarter API command-line interface 'undeploy' view"""

    def post(self, request, kind: str, *args, **kwargs):
        return self.broker.undeploy(request=request, kwargs=kwargs)
