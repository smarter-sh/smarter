"""
This file contains the mixins for the provider model.
"""

# pylint: disable=W0613
import logging
from typing import Optional

from django.db.models import Sum
from django.db.models.query import QuerySet

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.models import Charge
from smarter.apps.account.tasks import create_charge
from smarter.apps.prompt.models import Chat, ChatHistory, ChatPluginUsage, ChatToolCall
from smarter.apps.prompt.tasks import (
    create_chat_plugin_usage,
    create_chat_tool_call_history,
)
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.common.exceptions import SmarterValueError
from smarter.lib.cache import cache_results
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class InternalKeys:
    """
    This class contains the internal keys for the provider model.
    """

    PromptTokens = "prompt_tokens"
    CompletionTokens = "completion_tokens"
    TotalTokens = "total_tokens"


class ChatDbMixin(AccountMixin):
    """
    This mixin contains the database related methods for the provider model.
    """

    __slots__ = ("_chat", "_chat_tool_call", "_chat_plugin_usage", "_charges", "_chat_history", "_message_history")

    def __init__(self, *args, **kwargs):
        """
        Constructor method for the ChatDbMixin class.
        """

        @cache_results()
        def cached_chat_by_session_key(session_key: str) -> Chat:
            return Chat.objects.get(session_key=session_key)

        self._chat: Optional[Chat] = None
        self._chat_tool_call: Optional[ChatToolCall] = None
        self._chat_plugin_usage: Optional[ChatPluginUsage] = None
        self._charges: Optional[QuerySet[Charge]] = None
        self._chat_history: Optional[QuerySet[ChatHistory]] = None
        self._message_history: Optional[list[dict]] = None
        super().__init__(*args, **kwargs)
        session_key = kwargs.get(SMARTER_CHAT_SESSION_KEY_NAME, None)
        if session_key:
            self._chat = cached_chat_by_session_key(session_key=session_key)
        else:
            self._chat = kwargs.get("chat", None)

    @property
    def ready(self) -> bool:
        """
        This method returns the ready status.
        """
        super_ready = bool(super().ready)
        chat_ready = True if self.chat else False
        return super_ready and chat_ready

    @property
    def chat(self) -> Optional[Chat]:
        """
        This method returns the chat instance.
        """
        return self._chat

    @chat.setter
    def chat(self, value: Chat):
        """
        This method sets the chat instance.
        """
        if not isinstance(value, Chat) and not value is None:
            raise SmarterValueError("Chat must be an instance of Chat or None")
        self._chat = value
        self._chat = None
        self._chat_tool_call = None
        self._chat_plugin_usage = None
        self._charges = None
        self._chat_history = None
        self._message_history = None

    @property
    def chat_history(self) -> Optional[QuerySet[ChatHistory]]:
        """
        This method returns the chat history instance.
        """
        if self._chat_history is None and self.chat is not None:
            self._chat_history = ChatHistory.objects.filter(chat=self.chat)
        return self._chat_history

    @property
    def db_message_history(self) -> Optional[list[dict]]:
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
    def db_chat_tool_call(self) -> Optional[ChatToolCall]:
        """
        This method returns the chat tool call instance.
        """

        @cache_results()
        def cached_chat_tool_call_by_chat_id(chat_id: int) -> ChatToolCall:
            return ChatToolCall.objects.get(chat_id=chat_id)

        if self._chat_tool_call is None and self.chat is not None:
            self._chat_tool_call = cached_chat_tool_call_by_chat_id(chat_id=self.chat.id)  # type: ignore
        return self._chat_tool_call

    @property
    def db_chat_plugin_usage(self) -> Optional[ChatPluginUsage]:
        """
        This method returns the chat plugin usage instance.
        """

        @cache_results()
        def cached_chat_plugin_usage_by_chat_id(chat_id: int) -> ChatPluginUsage:
            return ChatPluginUsage.objects.get(chat_id=chat_id)

        if self._chat_plugin_usage is None and self.chat is not None:
            self._chat_plugin_usage = cached_chat_plugin_usage_by_chat_id(chat_id=self.chat.id)  # type: ignore
        return self._chat_plugin_usage

    @property
    def db_charges(self) -> Optional[QuerySet[Charge]]:
        """
        This method returns the charge instance.
            prompt_tokens = models.IntegerField()
            completion_tokens = models.IntegerField()
            total_tokens = models.IntegerField()

        """

        if self._charges is None and self.account is not None and self.chat is not None:
            self._charges = Charge.objects.filter(account=self.account, session_key=self.chat.session_key)
        return self._charges

    @property
    def db_total_prompt_tokens(self) -> int:
        """
        This method returns the prompt tokens.
        """
        return self.db_charges.aggregate(Sum("prompt_tokens"))["prompt_tokens__sum"] if self.db_charges else 0

    @property
    def db_total_completion_tokens(self) -> int:
        """
        This method returns the completion tokens.
        """
        return self.db_charges.aggregate(Sum("completion_tokens"))["completion_tokens__sum"] if self.db_charges else 0

    @property
    def db_total_total_tokens(self) -> int:
        """
        This method returns the total tokens.
        """
        return self.db_charges.aggregate(Sum("total_tokens"))["total_tokens__sum"] if self.db_charges else 0

    @property
    def db_total_tokens(self) -> Optional[dict]:
        if self.db_charges is None:
            return None
        return {
            InternalKeys.PromptTokens: self.db_total_prompt_tokens,
            InternalKeys.CompletionTokens: self.db_total_completion_tokens,
            InternalKeys.TotalTokens: self.db_total_total_tokens,
        }

    def db_refresh(self):
        """
        This method refreshes the provider instance.
        """
        if self.chat:
            self.chat.refresh_from_db()
        self._charges = None
        # pylint: disable=W0104
        self.db_charges

    def db_insert_chat_tool_call(self, *args, **kwargs):
        """
        This method inserts the chat tool call instance.
        """
        if not self.chat:
            return
        chat_id = self.chat.id  # type: ignore
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
        chat_id = chat.id  # type: ignore
        plugin = kwargs.get("plugin", None)
        plugin_id = plugin.id if plugin else None
        input_text = kwargs.get("input_text", None)
        create_chat_plugin_usage.delay(chat_id=chat_id, plugin_id=plugin_id, input_text=input_text)

    def db_insert_charge(self, provider, charge_type, completion_tokens, prompt_tokens, total_tokens, model, reference):
        """
        This method inserts a new charge record.
            provider=self.provider,
            charge_type=charge_type,
            completion_tokens=self.completion_tokens,
            prompt_tokens=self.prompt_tokens,
            total_tokens=self.total_tokens,
            model=self.model,
            reference=self.reference or "ChatProviderBase._insert_charge_by_type()",

        """
        if not self.account:
            raise SmarterValueError("Account is required to create a charge record.")
        if not self.chat:
            raise SmarterValueError("Chat is required to create a charge record.")
        if not self.user:
            logger.warning("Creating a charge record with no User.")

        create_charge.delay(
            account_id=self.account.id,  # type: ignore
            user_id=self.user.id if self.user else None,  # type: ignore
            session_key=self.chat.session_key,
            provider=provider,
            charge_type=charge_type,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model=model,
            reference=reference,
        )
