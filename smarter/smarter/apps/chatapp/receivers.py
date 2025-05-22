"""Receiver functions for chatapp signals."""

# pylint: disable=W0613

from logging import getLogger

from django.dispatch import receiver

from smarter.common.helpers.console_helpers import formatted_text

from .signals import chat_config_invoked, chat_session_invoked
from .views import ChatConfigView, SmarterChatSession


logger = getLogger(__name__)


# chat_session_invoked.send(sender=self.__class__, instance=self, request=request)
@receiver(chat_session_invoked, dispatch_uid="chat_session_invoked")
def handle_chat_session_invoked(sender, instance: SmarterChatSession, request, *args, **kwargs):
    """Handle chat session invoked signal."""
    url: str = None
    if request is not None:
        url = request.build_absolute_uri()

    logger.info(
        "%s.%s %s - %s", formatted_text("smarter.apps.chatapp.receivers.chat_session_invoked"), sender, instance, url
    )


@receiver(chat_config_invoked, dispatch_uid="chat_config_invoked")
def handle_chat_config_invoked_(sender, instance: ChatConfigView, request, *args, **kwargs):
    """Handle chat config invoked signal."""
    url: str = None
    if request is not None:
        url = request.build_absolute_uri()

    logger.info(
        "%s.%s %s - %s", formatted_text("smarter.apps.chatapp.receivers.chat_config_invoked_"), sender, instance, url
    )
