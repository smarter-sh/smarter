"""
This file contains the mixins for the provider model.
"""

# pylint: disable=W0613

from django.db.models import Sum
from django.db.models.query import QuerySet

from smarter.apps.account.models import Account, Charge
from smarter.apps.account.tasks import create_charge
from smarter.apps.chat.models import Chat, ChatPluginUsage, ChatToolCall
from smarter.apps.chat.tasks import (
    create_chat_plugin_usage,
    create_chat_tool_call_history,
    update_chat,
)


class InternalKeys:
    """
    This class contains the internal keys for the provider model.
    """

    PromptTokens = "prompt_tokens"
    CompletionTokens = "completion_tokens"
    TotalTokens = "total_tokens"


class ProviderDbMixin:
    """
    This mixin contains the database related methods for the provider model.
    """

    __slots__ = ("_chat", "_chat_tool_call", "_chat_plugin_usage", "_charges", "_session_key")

    _chat: Chat
    _chat_tool_call: ChatToolCall
    _chat_plugin_usage: ChatPluginUsage
    _charges: QuerySet[Charge]

    def __init__(self, *args, **kwargs):
        """
        Constructor method for the ProviderDbMixin class.
        """
        super().__init__(*args, **kwargs)
        self._session_key = kwargs.get("session_key", None)
        self._chat = kwargs.get("chat", None)

        self._chat_tool_call = None
        self._chat_plugin_usage = None
        self._charges = None

    @property
    def ready(self) -> bool:
        """
        This method returns the ready status.
        """
        super_ready = super().ready
        chat_ready = self.chat.ready if self.chat else False
        return super_ready and chat_ready

    @property
    def chat(self) -> Chat:
        """
        This method returns the chat instance.
        """
        if self._chat is None and self.session_key is not None:
            self._chat = Chat.objects.get(session_key=self.session_key)
            self._session_key = self._chat.session_key
        return self._chat

    @property
    def session_key(self) -> str:
        """
        This method returns the session key.
        """
        return self.chat.session_key if self.chat else None

    @property
    def account(self) -> Account:
        """
        This method returns the account instance.
        """
        return self.chat.account if self.chat else None

    @property
    def chat_tool_call(self) -> ChatToolCall:
        """
        This method returns the chat tool call instance.
        """
        if self._chat_tool_call is None and self.chat is not None:
            self._chat_tool_call = ChatToolCall.objects.get(chat=self.chat)
        return self._chat_tool_call

    @property
    def chat_plugin_usage(self) -> ChatPluginUsage:
        """
        This method returns the chat plugin usage instance.
        """
        if self._chat_plugin_usage is None and self.chat is not None:
            self._chat_plugin_usage = ChatPluginUsage.objects.get(chat=self.chat)
        return self._chat_plugin_usage

    @property
    def charges(self) -> QuerySet[Charge]:
        """
        This method returns the charge instance.
            prompt_tokens = models.IntegerField()
            completion_tokens = models.IntegerField()
            total_tokens = models.IntegerField()

        """
        if self._charges is None and self.account is not None and self.session_key is not None:
            self._charges = Charge.objects.get(account=self.account, session_key=self.session_key)
        return self._charges

    @property
    def total_prompt_tokens(self) -> int:
        """
        This method returns the prompt tokens.
        """
        return self.charges.aggregate(Sum("prompt_tokens"))["prompt_tokens__sum"] if self.charges else 0

    @property
    def total_completion_tokens(self) -> int:
        """
        This method returns the completion tokens.
        """
        return self.charges.aggregate(Sum("completion_tokens"))["completion_tokens__sum"] if self.charges else 0

    @property
    def total_total_tokens(self) -> int:
        """
        This method returns the total tokens.
        """
        return self.charges.aggregate(Sum("total_tokens"))["total_tokens__sum"] if self.charges else 0

    @property
    def total_tokens(self) -> dict:
        if self.charges is None:
            return None
        return {
            InternalKeys.PromptTokens: self.total_prompt_tokens,
            InternalKeys.CompletionTokens: self.total_completion_tokens,
            InternalKeys.TotalTokens: self.total_total_tokens,
        }

    def save(self, *args, **kwargs):
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

    def refresh(self):
        """
        This method refreshes the provider instance.
        """
        if self.chat:
            self.chat.refresh_from_db()
        self._charges = None
        # pylint: disable=W0104
        self.charges
        super().refresh()

    def insert_chat_tool_call(self, *args, **kwargs):
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

    def insert_chat_plugin_usage(self, *args, **kwargs):
        """
        This method inserts the chat plugin usage instance.
        """
        if not self.chat:
            return
        chat_id = self.chat.id
        plugin = kwargs.get("plugin", None)
        plugin_id = plugin.id if plugin else None
        input_text = kwargs.get("input_text", None)
        create_chat_plugin_usage.delay(chat_id, plugin_id, input_text)

    def insert_charge(self, *args, **kwargs):
        """
        This method inserts a new charge record.
        """
        if not self.account:
            return
        user = (kwargs.get("user", None),)

        create_charge.delay(
            account_id=self.account.id,
            user_id=user.id if user else None,
            session_key=self.session_key,
            provider=kwargs.get("provider", None),
            charge_type=kwargs.get("charge_type", None),
            prompt_tokens=kwargs.get("prompt_tokens", None),
            completion_tokens=kwargs.get("completion_tokens", None),
            total_tokens=kwargs.get("total_tokens", None),
            model=kwargs.get("model", None),
            reference=kwargs.get("reference", None),
        )
