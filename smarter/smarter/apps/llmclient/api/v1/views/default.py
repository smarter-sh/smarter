# pylint: disable=W0611
"""Smarter Customer API view."""

import traceback

from smarter.apps.llmclient.models import LLMClient
from smarter.apps.prompt.contract.builders import PromptChatApiErrorInternal
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .base import LLMClientApiBaseViewSet

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING])


class DefaultLLMClientApiView(LLMClientApiBaseViewSet):
    """
    Main view for Smarter LLMClient API prompts.

    The top-level viewset for customer-deployed Plugin-based Prompt APIs.
    """

    def dispatch(self, request, *args, **kwargs):
        """
        Smarter API LLMClient dispatch method.

        :param request: Django HttpRequest object
        :param args: Additional positional arguments
        :param name: LLMClient name (str, optional)
        :param kwargs: Additional keyword arguments

        **Example request payload**:

        .. code-block:: json

           {
               "session_key": "dde3dde5e3b97134f5bce5edf26ec05134da71d8485a86dfc9231149aaf0b0af",
               "messages": [
                   {
                       "role": "assistant",
                       "content": "Welcome to Smarter!.  how can I assist you today?"
                   },
                   {
                       "role": "user",
                       "content": "Hello, World!"
                   }
               ]
           }
        """
        hashed_id = kwargs.pop("hashed_id", None)
        if hashed_id:
            self._llmclient_id = LLMClient.id_from_hashed_id(hashed_id)
        else:
            self._llmclient_id = kwargs.pop("llmclient_id", None)
        self._name = kwargs.pop("name", None)
        logger.info("%s.dispatch() %s %s", self.formatted_class_name, self.llmclient, self.user_profile)

        try:
            retval = super().dispatch(request, *args, **kwargs)
        # pylint: disable=broad-except
        except Exception as e:
            # logged, never returned: the client receives the error envelope, without a stack trace.
            logger.error("DefaultLLMClientApiView.dispatch: %s, %s", e, traceback.format_exc())
            retval = self.error_response(
                request, PromptChatApiErrorInternal("An error occurred while processing your request.")
            )
        return retval
