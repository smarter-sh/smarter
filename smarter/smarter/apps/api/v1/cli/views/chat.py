# pylint: disable=W0613
"""Smarter API command-line interface 'chat' view"""

from .base import CliBaseApiView


class ApiV1CliChatApiView(CliBaseApiView):
    """Smarter API command-line interface 'chat' view"""

    def post(self, request, *args, **kwargs):
        print("ApiV1CliChatApiView.post kwargs:", kwargs)
        return self.broker.chat(request=request, kwargs=kwargs)
