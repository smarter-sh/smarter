# pylint: disable=W0613
"""Smarter API command-line interface 'chat' view"""

from smarter.apps.api.v1.manifests.enum import SAMKinds

from .base import APIV1CLIViewError, CliBaseApiView


class ApiV1CliChatApiView(CliBaseApiView):
    """Smarter API command-line interface 'chat' view"""

    def post(self, request, *args, **kwargs):
        if self.manifest_kind != SAMKinds.CHAT.value:
            raise APIV1CLIViewError(
                f"Invalid manifest kind. Was expecting {SAMKinds.CHAT.value} but received {self.manifest_kind}"
            )
        return self.broker.chat(request=request, kwargs=kwargs)
