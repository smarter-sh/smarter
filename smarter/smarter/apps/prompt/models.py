# pylint: disable=W0613,C0115
"""All models for the OpenAI Function Calling API app."""

from functools import cached_property
from typing import Any, Optional, Union

from django.db import models
from django.db.utils import IntegrityError
from django.http import HttpRequest
from rest_framework import serializers

from smarter.apps.account.models import (
    MetaDataWithOwnershipModel,
    MetaDataWithOwnershipModelManager,
)
from smarter.apps.llm_client.models import LLMClient, get_cached_llm_client_by_request
from smarter.apps.plugin.models import PluginMeta
from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.lib import json, logging
from smarter.lib.cache import lazy_cache as cache
from smarter.lib.django import waffle
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.django.waffle import SmarterWaffleSwitches


def should_log_verbose(level) -> bool:
    return smarter_settings.verbose_logging


logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING])
logger_verbose = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING], condition_func=should_log_verbose
)


class Chat(MetaDataWithOwnershipModel):
    """Chat model."""

    class Meta:
        verbose_name_plural = "Chats"
        unique_together = (SMARTER_CHAT_SESSION_KEY_NAME, "url")

    objects: MetaDataWithOwnershipModelManager["Chat"] = MetaDataWithOwnershipModelManager()

    session_key = models.CharField(max_length=255, blank=False, null=False, unique=True)
    llm_client = models.ForeignKey(LLMClient, on_delete=models.CASCADE, blank=False, null=False)
    ip_address = models.GenericIPAddressField(blank=False, null=False)
    user_agent = models.CharField(max_length=255, blank=False, null=False)
    url = models.URLField(blank=False, null=False)

    def __str__(self):
        # pylint: disable=E1136
        return f"{self.id} - {self.ip_address} - {self.url}"  # type: ignore[return]

    def delete(self, *args, **kwargs):
        if self.session_key:
            cache.delete(self.session_key)
        super().delete(*args, **kwargs)


class PromptHistory(TimestampedModel):
    """Prompt history model."""

    class Meta:
        verbose_name_plural = "Prompt History"

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    request = models.JSONField(
        blank=True,
        null=True,
        encoder=json.SmarterJSONEncoder,
    )
    response = models.JSONField(
        blank=True,
        null=True,
        encoder=json.SmarterJSONEncoder,
    )
    messages = models.JSONField(
        blank=True,
        null=True,
        encoder=json.SmarterJSONEncoder,
    )

    def __str__(self):
        return f"{self.chat.id}"  # type: ignore[return]

    @property
    def chat_history(self) -> list[dict]:
        """Used by the Reactapp (via PromptConfigView) to display the chat history."""
        history = self.messages if self.messages else self.request.get("messages", []) if self.request else []
        # response = self.response.get("choices", []) if self.response else []
        # response = response[0] if response else {}
        # response = response.get("message", {})
        # history.append(response)
        return history


class PromptToolCall(TimestampedModel):
    """Prompt tool call history model."""

    class Meta:
        verbose_name_plural = "Prompt Tool Call History"

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    plugin = models.ForeignKey(PluginMeta, on_delete=models.CASCADE, blank=True, null=True)
    function_name = models.CharField(max_length=255, blank=True, null=True)
    function_args = models.CharField(max_length=255, blank=True, null=True)
    request = models.JSONField(
        blank=True,
        null=True,
        encoder=json.SmarterJSONEncoder,
    )
    response = models.JSONField(
        blank=True,
        null=True,
        encoder=json.SmarterJSONEncoder,
    )

    @classmethod
    def get_cached_object(
        cls, *args, invalidate: Optional[bool] = False, pk: Optional[int] = None, **kwargs
    ) -> Optional["PromptToolCall"]:
        """
        Get the PromptToolCall instance for the given primary key from the cache.

        This method retrieves the PromptToolCall instance associated with the given primary key
        from the cache. If the instance is not found in the cache, it attempts to
        retrieve it from the database. If it still cannot be found, it returns ``None``.

        :param invalidate: Whether to invalidate the cache before retrieving the object.
        :type invalidate: Optional[bool]
        :param pk: The primary key of the PromptToolCall instance to retrieve.
        :type pk: Optional[int]

        :returns: The PromptToolCall instance associated with the given primary key, or ``None`` if not found.
        :rtype: Optional[PromptToolCall]
        """
        return super().get_cached_object(*args, invalidate=invalidate, pk=pk, **kwargs)  # type: ignore[return]

    def __str__(self):
        if self.plugin:
            name = f"{self.chat.id} - {self.plugin.name}"  # type: ignore[return]
        else:
            name = f"{self.chat.id} - {self.function_name}"  # type: ignore[return]
        return name


class PromptPluginUsage(TimestampedModel):
    """Plugin selection history model."""

    class Meta:
        verbose_name_plural = "Prompt Plugin Usage"

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    plugin = models.ForeignKey(PluginMeta, on_delete=models.CASCADE)
    input_text = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.chat.id} - {self.plugin.name}"  # type: ignore[return]


# --------------------------------------------------------------------------------
# Serializers
# --------------------------------------------------------------------------------
class PromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = "__all__"


class PromptToolCallSerializer(serializers.ModelSerializer):
    """Serializer for the PromptToolCall model."""

    chat = PromptSerializer(read_only=True)

    class Meta:
        model = PromptToolCall
        fields = "__all__"


class PromptPluginUsageSerializer(serializers.ModelSerializer):
    """Serializer for the PromptPluginUsage model."""

    chat = PromptSerializer(read_only=True)

    class Meta:
        model = PromptPluginUsage
        fields = "__all__"


class PromptHelper(SmarterRequestMixin):
    """
    Helper class for working with :class:`Chat` objects.

    This class provides methods for creating and retrieving :class:`Chat` objects,
    as well as managing the cache for chat sessions. It is designed to simplify
    the process of interacting with chat-related data and to ensure consistent
    handling of chat sessions, llm_clients, and associated metadata.

    **Features**

    - Abstracts the logic for creating and retrieving chat sessions.
    - Manages caching of chat objects to improve performance and reduce database queries.
    - Provides access to related chat history, tool calls, and plugin usage.
    - Integrates with Django's request and session handling.
    - Ensures that chat sessions are always associated with a valid :class:`LLMClient` and :class:`Account`.

    **Usage**

    Typically, this class is instantiated with a Django :class:`HttpRequest` object and a session key.
    Optionally, a :class:`LLMClient` instance can be provided to associate the chat session with a specific llm_client.

    Example
    -------
    .. code-block:: python

        helper = PromptHelper(request, session_key)
        if helper.ready:
            chat = helper.chat
            llm_client = helper.llm_client
            history = helper.history

    :param request: The Django HttpRequest object for the current session.
    :type request: django.http.HttpRequest
    :param session_key: The session key identifying the chat session.
    :type session_key: Optional[str]
    :param llm_client: An optional LLMClient instance to associate with the chat session.
    :type llm_client: Optional[LLMClient]
    :param args: Additional positional arguments.
    :param kwargs: Additional keyword arguments.

    :raises SmarterValueError: If neither a session key nor a LLMClient instance is provided.
    :raises SmarterConfigurationError: If there is an error creating a new Chat object.

    .. note::
        This class is intended for internal use within the Smarter platform and
        should not be used directly in user-facing code without proper validation.

    .. todo::
        - Remove the session_key parameter and rely solely on the LLMClient instance for chat session management.

    .. seealso::
        - :class:`smarter.apps.llm_client.models.LLMClient`
        - :class:`smarter.apps.account.models.Account`
        - :class:`smarter.apps.chat.models.Chat`
        - :class:`smarter.lib.django.request.SmarterRequestMixin`
    """

    _chat: Optional[Chat] = None
    _llm_client: Optional[LLMClient] = None
    _prompt_tool_call: Optional[Union[models.QuerySet, list]] = None
    _prompt_plugin_usage: Optional[Union[models.QuerySet, list]] = None
    _history: Optional[dict] = None

    def __init__(
        self, request: HttpRequest, session_key: Optional[str], *args, llm_client: Optional[LLMClient] = None, **kwargs
    ) -> None:
        """
        Initialize the PromptHelper instance.

        :param request: The Django HttpRequest object for the current session.
        :type request: django.http.HttpRequest
        :param session_key: The session key identifying the chat session.
        :type session_key: Optional[str]
        :param llm_client: An optional LLMClient instance to associate with the chat session.
        :type llm_client: Optional[LLMClient]
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :raises SmarterValueError: If neither a session key nor a LLMClient instance is provided.
        :raises SmarterConfigurationError: If there is an error creating a new Chat object.
        """
        logger_verbose.debug(
            "%s.__init__() - received request: %s session_key: %s, llm_client: %s",
            self.formatted_class_name,
            self.smarter_build_absolute_uri(request),
            session_key,
            llm_client,
        )
        if not request:
            raise SmarterValueError(f"{self.formatted_class_name} request object is required.")
        super().__init__(request, session_key=session_key, **kwargs)
        self._chat = None
        self._llm_client = llm_client
        self._prompt_tool_call = None
        self._prompt_plugin_usage = None
        self._history = None

        if not session_key and not llm_client:
            raise SmarterValueError(
                f"{self.formatted_class_name} either a session_key or a LLMClient instance is required"
            )

        if llm_client and llm_client.user_profile:
            logger_verbose.debug("%s.__init__() received LLMClient instance: %s", self.formatted_class_name, llm_client)
            logger_verbose.debug(
                "%s.__init__() - reinitializing AccountMixin from llm_client.user_profile: %s",
                self.formatted_class_name,
                llm_client.user_profile,
            )
            self._user_profile = llm_client.user_profile
            self._account = llm_client.user_profile.account
            self._user = llm_client.user_profile.user

        if session_key:
            self._session_key = session_key
            logger_verbose.debug(
                "%s.__init__() - setting session_key to %s from session_key parameter",
                self.formatted_class_name,
                self._session_key,
            )
        if self.session_key:
            logger_verbose.debug("%s.__init__() received session_key: %s", self.formatted_class_name, session_key)
            self._chat = self.get_cached_chat()

        logger_verbose.debug(
            "%s.__init__() - %s with session_key: %s, chat: %s",
            self.formatted_class_name,
            "is ready" if self.ready else "is not ready",
            self.session_key,
            self._chat,
        )

    def __str__(self):
        return self.session_key

    @property
    def ready(self) -> bool:
        """
        Check if the PromptHelper is ready to use.

        This property returns ``True`` if the chat instance is available and all required
        attributes are set, otherwise returns ``False``. It is useful for determining
        whether the PromptHelper is fully initialized and ready for chat operations.

        :returns: ``True`` if the PromptHelper is ready to use, otherwise ``False``.
        :rtype: bool
        """
        return bool(super().ready) and bool(self._session_key) and bool(self._chat) and bool(self._llm_client)

    def to_json(self) -> dict[str, Any]:
        """
        Convert the PromptHelper instance to a JSON serializable dictionary.

        This method returns a dictionary representation of the PromptHelper instance,
        including key metadata and related objects such as the chat, llm_client, chat history,
        and a unique client string.

        :returns: A dictionary containing the serialized state of the PromptHelper.
        :rtype: dict[str, Any]
        """
        return self.sorted_dict(
            {
                **super().to_json(),
                "ready": self.ready,
                "session_key": self.session_key,
                "chat": self.chat.id if self.chat else None,  # type: ignore[return]
                "llm_client": self.llm_client.id if self.llm_client else None,  # type: ignore[return]
                "history": self.history,
                "unique_client_string": self.unique_client_string,
            }
        )

    @cached_property
    def formatted_class_name(self) -> str:
        """
        Returns the formatted class name for the PromptHelper.

        This property returns a string representation of the class name,
        formatted to include the parent class's formatted name and the
        ``PromptHelper`` class. This is useful for logging and debugging
        purposes, as it provides a clear and consistent identifier for
        instances of this helper class.

        Example
        -------
        .. code-block:: python

            helper = PromptHelper(request, session_key)
            helper.formatted_class_name
            # 'SmarterRequestMixin.PromptHelper()'

        :returns: The formatted class name as a string, including the parent class name.
        :rtype: str
        """
        class_name = f"{__name__}.{PromptHelper.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    @property
    def chat(self):
        """
        Get the chat instance for the current request.

        :returns: The Chat instance associated with the current session.
        :rtype: Chat
        """
        return self._chat

    @property
    def llm_client(self):
        """
        Returns a lazy instance of the LLMClient.

        Examples
        --------
        - ``https://hr.3141-5926-5359.alpha.api.example.com/llm-client/``
          returns ``LLMClient(name='hr', account=Account(...))``

        :returns: The LLMClient instance.
        :rtype: LLMClient
        """
        if self._llm_client:
            return self._llm_client
        self._llm_client = get_cached_llm_client_by_request(request=self.smarter_request)

    @property
    def chat_history(self) -> Union[models.QuerySet, list]:
        """
        Get the most recent chat history for the current chat session.

        :returns: The most recent PromptHistory instance's chat_history field, or an empty list if none found.
        :rtype: Union[models.QuerySet, list]
        """
        rec = PromptHistory.objects.filter(chat=self.chat).order_by("-created_at").first()
        return rec.chat_history if rec else []

    @property
    def prompt_tool_call(self) -> Union[models.QuerySet, list]:
        """
        Get the most recent chat tool call history for the current chat session.

        :returns: A queryset of PromptToolCall instances for the current chat session, ordered by creation date.
        :rtype: Union[models.QuerySet, list]
        """
        if self._prompt_tool_call:
            return self._prompt_tool_call
        self._prompt_tool_call = PromptToolCall.objects.filter(chat=self.chat).order_by("-created_at") or []
        return self._prompt_tool_call

    @property
    def prompt_plugin_usage(self) -> Union[models.QuerySet, list]:
        """
        Get the most recent chat plugin usage history for the current chat session.

        :returns: A queryset of PromptPluginUsage instances for the current chat session, ordered by creation date.
        :rtype: Union[models.QuerySet, list]
        """
        if self._prompt_plugin_usage:
            return self._prompt_plugin_usage
        self._prompt_plugin_usage = PromptPluginUsage.objects.filter(chat=self.chat).order_by("-created_at") or []
        return self._prompt_plugin_usage

    @property
    def history(self) -> dict:
        """
        Serialize the most recent logged history output for the chat session.

        :returns: A dictionary containing serialized chat, chat history, tool calls, and plugin usage.
        :rtype: dict
        """
        if self._history:
            return self._history
        chat_serializer = PromptSerializer(self.chat)
        prompt_tool_call_serializer = PromptToolCallSerializer(self.prompt_tool_call, many=True)
        prompt_plugin_usage_serializer = PromptPluginUsageSerializer(self.prompt_plugin_usage, many=True)
        self._history = {
            "chat": chat_serializer.data,
            "chat_history": self.chat_history,
            "prompt_tool_call_history": prompt_tool_call_serializer.data,
            "prompt_plugin_usage_history": prompt_plugin_usage_serializer.data,
            # these two will be added upstream.
            "llm_client_request_history": None,  # LLMClientRequests
        }
        return self._history

    def get_cached_chat(self) -> Optional[Chat]:
        """
        Get the chat instance for the current request.

        This method retrieves the Chat instance associated with the current session key
        from the cache. If the Chat instance is not found in the cache, it attempts to
        retrieve it from the database. If it still cannot be found, a new Chat instance
        is created using the provided LLMClient and request metadata.

        :returns: The Chat instance associated with the current session, or ``None`` if not found.
        :rtype: Optional[Chat]
        """
        if not self.smarter_request:
            logger.error("%s - request object is required for PromptHelper.", self.formatted_class_name)
            return None

        chat: Chat = cache.get(self.session_key)  # type: ignore[assignment]
        if chat:
            logger_verbose.debug(
                "%s - retrieved cached Chat: %s session_key: %s", self.formatted_class_name, chat, chat.session_key
            )
            return chat

        if self.session_key:
            try:
                chat = Chat.objects.get(session_key=self.session_key)
                logger_verbose.debug(
                    "%s - retrieved Chat instance: %s session_key: %s",
                    self.formatted_class_name,
                    chat,
                    chat.session_key,
                )
            except Chat.DoesNotExist:
                pass

        if not chat:
            if not self.llm_client:
                raise SmarterValueError(
                    f"{self.formatted_class_name} LLMClient instance is required for creating a Chat object."
                )

            try:
                # modify the unit test server URL
                # to a more Django friendly URL.
                django_friendly_url = self.url or ""
                django_friendly_url = django_friendly_url.replace("http://testserver/", "http://testserver.local/")
                chat = Chat.objects.create(
                    session_key=self.session_key,
                    user_profile=self.user_profile,
                    llm_client=self.llm_client,
                    ip_address=self.ip_address,
                    user_agent=self.user_agent,
                    url=django_friendly_url,
                )
            except IntegrityError as e:
                raise SmarterConfigurationError(f"{self.formatted_class_name} - IntegrityError: {str(e)}") from e

        cache.set(key=self.session_key, value=chat, timeout=smarter_settings.chat_cache_expiration or 300)
        if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
            logger_verbose.debug(
                "%s - cached chat instance: %s session_key: %s", self.formatted_class_name, chat, chat.session_key
            )

        if not chat.llm_client:
            raise ValueError(f"{self.formatted_class_name} LLMClient instance is required for Chat object.")

        return chat
