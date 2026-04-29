# pylint: disable=W0611
"""
Smarter Customer API view.
"""

import traceback
from http import HTTPStatus

from django.http import JsonResponse

import smarter.lib.logging as logging
from smarter.apps.chatbot.models import ChatBot
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .base import ChatBotApiBaseViewSet

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.CHATBOT_LOGGING])


class DefaultChatbotApiView(ChatBotApiBaseViewSet):
    """
    Main view for Smarter ChatBot API chat prompts.
    top-level viewset for customer-deployed Plugin-based Chat APIs.
    """

    def dispatch(self, request, *args, **kwargs):
        """
        Smarter API ChatBot dispatch method.

        :param request: Django HttpRequest object
        :param args: Additional positional arguments
        :param name: Chatbot name (str, optional)
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
            self._chatbot_id = ChatBot.id_from_hashed_id(hashed_id)
        else:
            self._chatbot_id = kwargs.pop("chatbot_id", None)
        self._name = kwargs.pop("name", None)
        logger.info("%s - dispatch() %s %s ", self.formatted_class_name, self.chatbot, self.user_profile)

        try:
            retval = super().dispatch(request, *args, **kwargs)
        # pylint: disable=broad-except
        except Exception as e:
            err_traceback = traceback.format_exc()
            logger.error("DefaultChatbotApiView.dispatch: %s, %s", e, err_traceback)
            retval = JsonResponse(
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
                data={
                    "error": "An error occurred while processing your request.",
                    "details": str(e),
                    "trace": err_traceback,
                },
            )
        return retval
