"""
This file contains the mixins for the provider model.
"""

# pylint: disable=W0613
import logging

from django.db.models import Sum
from django.db.models.query import QuerySet

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.models import Charge
from smarter.apps.account.tasks import create_charge
from smarter.apps.chat.models import Chat, ChatHistory, ChatPluginUsage, ChatToolCall
from smarter.apps.chat.tasks import (
    create_chat_plugin_usage,
    create_chat_tool_call_history,
    update_chat,
)
from smarter.common.exceptions import SmarterValueError


logger = logging.getLogger(__name__)


class InternalKeys:
    """
    This class contains the internal keys for the provider model.
    """

    PromptTokens = "prompt_tokens"
    CompletionTokens = "completion_tokens"
    TotalTokens = "total_tokens"


class ProviderDbMixin(AccountMixin):
    """
    This mixin contains the database related methods for the provider model.
    """

    __slots__ = ("_chat", "_chat_tool_call", "_chat_plugin_usage", "_charges", "_chat_history", "_message_history")

    def __init__(self, *args, **kwargs):
        """
        Constructor method for the ProviderDbMixin class.
        """
        self.init()
        super().__init__(*args, **kwargs)
        session_key = kwargs.get("session_key", None)
        if session_key:
            self._chat = Chat.objects.get(session_key=session_key)
        else:
            self._chat = kwargs.get("chat", None)

    def init(self):
        """
        This method initializes the provider instance.
        """
        self._chat: Chat = None
        self._chat_tool_call: ChatToolCall = None
        self._chat_plugin_usage: ChatPluginUsage = None
        self._charges: QuerySet[Charge] = None
        self._chat_history: QuerySet[ChatHistory] = None
        self._message_history: list[dict] = None

    @property
    def ready(self) -> bool:
        """
        This method returns the ready status.
        """
        super_ready = super().ready
        chat_ready = True if self.chat else False
        return super_ready and chat_ready

    @property
    def chat(self) -> Chat:
        """
        This method returns the chat instance.
        """
        return self._chat

    @chat.setter
    def chat(self, value: Chat):
        """
        This method sets the chat instance.
        """
        self.init()
        self._chat = value

    @property
    def chat_history(self) -> QuerySet[ChatHistory]:
        """
        This method returns the chat history instance.
        """
        if self._chat_history is None and self.chat is not None:
            self._chat_history = ChatHistory.objects.filter(chat=self.chat)
        return self._chat_history

    @property
    def db_message_history(self) -> list[dict]:
        """
        This method returns the most recently persisted
        messages in the chat history.
        """
        if self._message_history is not None:
            return self._message_history
        if self.chat_history and self.chat_history.exists():
            newest_record = self.chat_history.latest("created_at")
            if newest_record.messages:
                self._message_history = newest_record.messages
        return self._message_history

    @property
    def db_chat_tool_call(self) -> ChatToolCall:
        """
        This method returns the chat tool call instance.
        """
        if self._chat_tool_call is None and self.chat is not None:
            self._chat_tool_call = ChatToolCall.objects.get(chat=self.chat)
        return self._chat_tool_call

    @property
    def db_chat_plugin_usage(self) -> ChatPluginUsage:
        """
        This method returns the chat plugin usage instance.
        """
        if self._chat_plugin_usage is None and self.chat is not None:
            self._chat_plugin_usage = ChatPluginUsage.objects.get(chat=self.chat)
        return self._chat_plugin_usage

    @property
    def db_charges(self) -> QuerySet[Charge]:
        """
        This method returns the charge instance.
            prompt_tokens = models.IntegerField()
            completion_tokens = models.IntegerField()
            total_tokens = models.IntegerField()

        """
        if self._charges is None and self.account is not None and self.chat is not None:
            self._charges = Charge.objects.get(account=self.account, session_key=self.chat.session_key)
        return self._charges

    @property
    def db_total_prompt_tokens(self) -> int:
        """
        This method returns the prompt tokens.
        """
        return self.charges.aggregate(Sum("prompt_tokens"))["prompt_tokens__sum"] if self.db_charges else 0

    @property
    def db_total_completion_tokens(self) -> int:
        """
        This method returns the completion tokens.
        """
        return self.charges.aggregate(Sum("completion_tokens"))["completion_tokens__sum"] if self.db_charges else 0

    @property
    def db_total_total_tokens(self) -> int:
        """
        This method returns the total tokens.
        """
        return self.charges.aggregate(Sum("total_tokens"))["total_tokens__sum"] if self.db_charges else 0

    @property
    def db_total_tokens(self) -> dict:
        if self.charges is None:
            return None
        return {
            InternalKeys.PromptTokens: self.db_total_prompt_tokens,
            InternalKeys.CompletionTokens: self.db_total_completion_tokens,
            InternalKeys.TotalTokens: self.db_total_total_tokens,
        }

    def db_save(self, *args, **kwargs):
        """
        This method saves the chat instance associated with the session_key.
        """
        if self.chat:
            account = kwargs.get("account", self.account)
            chatbot = kwargs.get("chatbot", self.chat.chatbot)
            update_chat.delay(
                chat_id=self.chat.id,
                account_id=account.id if account else None,
                chatbot_id=chatbot.id if chatbot else None,
                ip_address=kwargs.get("ip_address", self.chat.ip_address),
                user_agent=kwargs.get("user_agent", self.chat.user_agent),
                url=kwargs.get("url", self.chat.url),
                request=kwargs.get("request", self.chat.request),
                response=kwargs.get("response", self.chat.response),
            )
        super().save(*args, **kwargs)

    def db_refresh(self):
        """
        This method refreshes the provider instance.
        """
        if self.chat:
            self.chat.refresh_from_db()
        self._charges = None
        # pylint: disable=W0104
        self.charges
        super().refresh()

    def db_insert_chat_tool_call(self, *args, **kwargs):
        """
        This method inserts the chat tool call instance.
        """
        if not self.chat:
            return
        chat_id = self.chat.id
        plugin = kwargs.get("plugin", None)
        plugin_id = plugin.id if plugin else None
        function_name = kwargs.get("function_name", None)
        function_args = kwargs.get("function_args", None)
        request = kwargs.get("request", None)
        response = kwargs.get("response", None)
        create_chat_tool_call_history.delay(chat_id, plugin_id, function_name, function_args, request, response)

    def db_insert_chat_plugin_usage(self, *args, **kwargs):
        """
        This method inserts the chat plugin usage instance.
        """
        chat = kwargs.get("chat", None)
        if not chat:
            logger.warning("db_insert_chat_plugin_usage() Chat is required to create a chat plugin usage record.")
            return
        chat_id = chat.id
        plugin = kwargs.get("plugin", None)
        plugin_id = plugin.id if plugin else None
        input_text = kwargs.get("input_text", None)
        create_chat_plugin_usage.delay(chat_id=chat_id, plugin_id=plugin_id, input_text=input_text)

    def db_insert_charge(self, *args, **kwargs):
        """
        This method inserts a new charge record.
        """
        if not self.account:
            raise SmarterValueError("Account is required to create a charge record.")
        if not self.chat:
            raise SmarterValueError("Chat is required to create a charge record.")
        if not self.user:
            logger.warning("Creating a charge record with no User.")

        create_charge.delay(
            account_id=self.account.id,
            user_id=self.user.id if self.user else None,
            session_key=self.chat.session_key,
            provider=kwargs.get("provider", None),
            charge_type=kwargs.get("charge_type", None),
            prompt_tokens=kwargs.get("prompt_tokens", None),
            completion_tokens=kwargs.get("completion_tokens", None),
            total_tokens=kwargs.get("total_tokens", None),
            model=kwargs.get("model", None),
            reference=kwargs.get("reference", None),
        )
