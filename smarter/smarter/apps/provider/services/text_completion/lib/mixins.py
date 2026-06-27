"""This file contains the mixins for the provider model."""

import logging
from typing import Optional

from django.db.models import Sum
from django.db.models.query import QuerySet

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.models import Charge, UserProfile
from smarter.apps.account.models.budget import charge_authorization
from smarter.apps.account.tasks import create_charge
from smarter.apps.prompt.models import (
    Prompt,
    PromptHistory,
    PromptPluginUsage,
    PromptToolCall,
)
from smarter.apps.prompt.tasks import (
    create_prompt_plugin_usage,
    create_prompt_tool_call_history,
)
from smarter.apps.provider.models import Provider
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class _InternalKeys:
    """This class contains the internal keys for the provider model."""

    PromptTokens = "prompt_tokens"
    CompletionTokens = "completion_tokens"
    TotalTokens = "total_tokens"


class ChatDbMixin(AccountMixin):
    """
    Mixin for database-related methods for provider models.

    This mixin provides database access and persistence logic for prompt provider
    models, including management of prompt sessions, prompt history, plugin/tool
    usage, and charge records. It is intended to be used as a base class for
    provider implementations that require integration with the Smarter database
    models. This provides layers of abstraction for asynchronously creating
    history and charge records resulting from provider requests.

    **Key Features:**

        - Manages retrieval and caching of prompt, prompt history, tool calls, plugin usage, and charge records.
        - Provides properties for accessing and updating prompt-related data.
        - Supports insertion of new tool call, plugin usage, and charge records via asynchronous tasks.
        - Aggregates token usage statistics for billing and analytics.

    **Usage:**

        Inherit from this mixin in a provider class to enable database-backed prompt session and usage tracking.

    **Example:**
        .. code-block:: python

            class MyProvider(ChatDbMixin):
                def custom_method(self):
                    # Access prompt history
                    history = self.prompt_history
                    # Insert a charge
                    self.db_insert_charge(...)
    """

    __slots__ = (
        "_chat",
        "_chat_tool_call",
        "_chat_plugin_usage",
        "_charges",
        "_chat_history",
        "_message_history",
        "_provider_name",
        "_provider",
        "_ready",
    )

    def __init__(self, *args, **kwargs):
        """
        Initialize the ChatDbMixin.

        This constructor sets up the database-related attributes for the
        provider model, including prompt session, tool call, plugin usage,
        charge, and prompt history references. It attempts to retrieve the
        current prompt session using a session key if provided, or falls
        back to a prompt object in kwargs.

        Parameters
        ----------
        *args : tuple
            Positional arguments passed to the superclass constructor.
        **kwargs : dict
            Keyword arguments passed to the superclass constructor. Recognized keys:
                - SMARTER_CHAT_SESSION_KEY_NAME (str): Default is 'session_key'. Session key for the prompt session.
                - prompt (Prompt): Prompt instance to use if session key is not provided.

        Example
        -------
        .. code-block:: python

            mixin = ChatDbMixin(prompt=my_chat)
            # or
            mixin = ChatDbMixin(session_key="abc123")
        """

        self._chat: Optional[Prompt] = None
        self._chat_tool_call: QuerySet[PromptToolCall] = None  # type: ignore
        self._chat_plugin_usage: Optional[QuerySet[PromptPluginUsage]] = None
        self._charges: Optional[QuerySet[Charge]] = None
        self._chat_history: Optional[QuerySet[PromptHistory]] = None
        self._message_history: Optional[list[dict]] = None
        self._provider_name: Optional[str] = kwargs.get("provider_name", None)
        self._provider: Optional[Provider] = kwargs.get("provider", None)
        self._ready: bool = False
        super().__init__(*args, **kwargs)
        session_key = kwargs.get(SMARTER_CHAT_SESSION_KEY_NAME, None)
        if session_key:
            self._chat = Prompt.get_cached_object(session_key=session_key)  # type: ignore
        else:
            self._chat = kwargs.get("prompt", None)

        if self.ready:
            logger.debug(
                "%s.__init__() initialized with prompt session key: %s",
                self.formatted_class_name,
                self.prompt.session_key if self.prompt else "None",
            )
        else:
            logger.warning("%s.__init__() initialized but not ready.", self.formatted_class_name)

    @property
    def ready(self) -> bool:
        """
        Indicates whether the mixin and its dependencies are ready for use.

        This property checks if both the superclass and the prompt instance are ready.
        It is useful for determining if the provider is fully initialized and can
        interact with the database and prompt session.

        Returns
        -------
        bool
            True if both the superclass and prompt are ready, False otherwise.

        Example
        -------
        .. code-block:: python

            if provider.ready:
                # Safe to proceed with database operations
                ...
        """
        if self._ready:
            return True
        super_ready = bool(super().ready)
        if not super_ready:
            logger.warning("%s.ready() is not ready because the superclass is not ready.", self.formatted_class_name)
            return False
        chat_ready = True if isinstance(self.prompt, Prompt) else False
        self._ready = chat_ready and super_ready
        if self._ready:
            logger.debug("%s.ready() is now ready for use.", self.formatted_class_name)
        else:
            logger.warning("%s.ready() is not ready because prompt is not set.", self.formatted_class_name)
        return self._ready

    @property
    def prompt(self) -> Optional[Prompt]:
        """
        Get the current prompt session instance.

        This property returns the active `Prompt` object associated with the provider,
        or `None` if no prompt session is set. It is used to access prompt-specific
        data and operations throughout the provider's logic.

        Returns
        -------
        Prompt or None
            The current prompt session instance, or None if not set.

        Example
        -------
        .. code-block:: python

            prompt = provider.prompt
            if prompt is not None:
                print(prompt.session_key)
        """
        return self._chat

    @prompt.setter
    def prompt(self, value: Prompt):
        """
        Set the current prompt session instance.

        This setter updates the active `Prompt` object for the provider. It also
        resetsall cached database-related attributes to ensure consistency
        with the new prompt session. If the provided value is not a `Prompt`
        instance or `None`, a `SmarterValueError` is raised.

        Parameters
        ----------
        value : Prompt or None
            The new prompt session instance to associate with the provider, or None to unset.

        Raises
        ------
        SmarterValueError
            If the value is not a `Prompt` instance or None.

        Side Effects
        ------------
        Resets lazy attributes: `_chat_tool_call`, `_chat_plugin_usage`, `_charges`,
        `_chat_history`, and `_message_history`.

        Example
        -------
        .. code-block:: python

            provider.prompt = new_chat
            # All cached database attributes are reset
        """
        if not isinstance(value, Prompt) and not value is None:
            raise SmarterValueError("Prompt must be an instance of Prompt or None")
        self._chat = value
        if isinstance(value, Prompt):
            logger.debug(
                "%s.prompt setter updated prompt session key to: %s", self.formatted_class_name, value.session_key
            )
        self._chat = None
        self._chat_tool_call = None  # type: ignore
        self._chat_plugin_usage = None  # type: ignore
        self._charges = None
        self._chat_history = None
        self._message_history = None
        logger.debug("%s.prompt setter reset lazy attributes due to prompt change.", self.formatted_class_name)

    @property
    def prompt_history(self) -> Optional[QuerySet[PromptHistory]]:
        """
        Get the prompt history queryset for the current prompt session.

        This property returns a Django QuerySet of `PromptHistory` objects associated
        with the current prompt session. If no prompt is set, or if there is no history,
        returns None. The queryset is cached for efficiency.

        Returns
        -------
        QuerySet[PromptHistory] or None
            QuerySet of prompt history records for the current prompt, or None if unavailable.

        Example
        -------
        .. code-block:: python

            history_qs = provider.prompt_history
            if history_qs is not None:
                for record in history_qs:
                    print(record.created_at, record.messages)
        """
        if self._chat_history is None and self.prompt is not None:
            self._chat_history = PromptHistory.objects.filter(prompt=self.prompt)
            logger.debug(
                "%s.prompt_history property loaded prompt history queryset with %d records.",
                self.formatted_class_name,
                self._chat_history.count(),
            )
        return self._chat_history

    @property
    def db_message_history(self) -> Optional[list[dict]]:
        """
        Get the most recently persisted messages in the prompt history.

        This property returns the latest list of messages stored in the prompt history
        for the current prompt session. If no messages are available, returns None.
        The result is cached for efficiency.

        Returns
        -------
        list[dict] or None
            The most recent list of message dictionaries from prompt history, or None if unavailable.

        Example
        -------
        .. code-block:: python

            messages = provider.db_message_history
            if messages:
                for msg in messages:
                    print(msg['role'], msg['content'])
        """
        if isinstance(self._message_history, list):
            return self._message_history
        if self.prompt_history and self.prompt_history.exists():
            newest_record = self.prompt_history.latest("created_at")
            if newest_record.messages:
                self._message_history = newest_record.messages
                if not isinstance(self._message_history, list):
                    logger.warning(
                        "%s.db_message_history expected messages to be a list but got %s.",
                        self.formatted_class_name,
                        type(self._message_history).__name__,
                    )
                logger.debug(
                    "%s.db_message_history property loaded %d messages from the latest prompt history record.",
                    self.formatted_class_name,
                    len(self._message_history) if isinstance(self._message_history, list) else 0,
                )
        return self._message_history

    @property
    def db_chat_tool_call(self) -> QuerySet[PromptToolCall]:
        """
        Get the queryset of prompt tool call records for the current prompt session.

        This property returns a Django QuerySet of `PromptToolCall` objects associated with
        the current prompt session. If no prompt is set, returns an empty queryset. The queryset
        is cached for efficiency.

        Returns
        -------
        QuerySet[PromptToolCall]
            QuerySet of prompt tool call records for the current prompt session, or an empty queryset if unavailable.

        Example
        -------
        .. code-block:: python

            tool_calls = provider.db_chat_tool_call
            for tool_call in tool_calls:
                print(tool_call.function_name, tool_call.created_at)
        """

        if self._chat_tool_call is None and self.prompt is not None:
            self._chat_tool_call = PromptToolCall.objects.filter(prompt=self.prompt)
            logger.debug(
                "%s.db_chat_tool_call() loaded prompt tool call queryset with %d records.",
                self.formatted_class_name,
                self._chat_tool_call.count(),
            )
            return self._chat_tool_call
        return PromptToolCall.objects.none()

    @property
    def db_chat_plugin_usage(self) -> QuerySet[PromptPluginUsage]:
        """
        Get the prompt plugin usage instance for the current prompt session.

        This property returns the `PromptPluginUsage` object associated with the
        current prompt session, if available. The result is cached for efficiency.
        If no prompt is set or no plugin usage exists, returns None.

        Returns
        -------
        PromptPluginUsage or None
            The prompt plugin usage instance for the current prompt, or None if unavailable.

        Example
        -------
        .. code-block:: python

            plugin_usage = provider.db_chat_plugin_usage
            if plugin_usage is not None:
                print(plugin_usage.plugin, plugin_usage.input_text)
        """

        if self._chat_plugin_usage is None and self.prompt is not None:
            self._chat_plugin_usage = PromptPluginUsage.objects.filter(prompt=self.prompt)
            logger.debug(
                "%s.db_chat_plugin_usage() loaded prompt plugin usage queryset with %d records.",
                self.formatted_class_name,
                self._chat_plugin_usage.count(),
            )
            return self._chat_plugin_usage
        return PromptPluginUsage.objects.none()

    @property
    def db_charges(self) -> QuerySet[Charge]:
        """
        Get the queryset of charge records for the current prompt session and UserProfile.

        This property returns a Django QuerySet of `Charge` objects filtered by the
        current user profile and prompt session key. If either the user profile or prompt is not set,
        returns None. The queryset is cached for efficiency.

        Each `Charge` record typically contains fields such as:
            - prompt_tokens (int): Number of prompt tokens used.
            - completion_tokens (int): Number of completion tokens used.
            - total_tokens (int): Total tokens used.

        Returns
        -------
        QuerySet[Charge] or None
            QuerySet of charge records for the current session, or None if unavailable.

        Example
        -------
        .. code-block:: python

            charges = provider.db_charges
            if charges is not None:
                for charge in charges:
                    print(charge.prompt_tokens, charge.completion_tokens, charge.total_tokens)
        """

        if self._charges is None and self.user_profile is not None and self.prompt is not None:
            self._charges = Charge.objects.filter(user_profile=self.user_profile, session_key=self.prompt.session_key)
            logger.debug(
                "%s.db_charges() loaded charge queryset with %d records.",
                self.formatted_class_name,
                self._charges.count(),
            )
        return Charge.objects.none()

    @property
    def db_total_prompt_tokens(self) -> int:
        """
        Get the total number of prompt tokens used in the current prompt session.

        This property aggregates the `prompt_tokens` field across all charge records
        for the current prompt session and account. If no charges are available, returns 0.

        Returns
        -------
        int
            The total number of prompt tokens used, or 0 if unavailable.

        Example
        -------
        .. code-block:: python

            total_prompt = provider.db_total_prompt_tokens
            print(f"Prompt tokens used: {total_prompt}")
        """
        if not self.db_charges.exists():
            return 0
        return self.db_charges.aggregate(Sum("prompt_tokens"))["prompt_tokens__sum"]

    @property
    def db_total_completion_tokens(self) -> int:
        """
        Get the total number of completion tokens used in the current prompt session.

        This property aggregates the `completion_tokens` field across all charge records
        for the current prompt session and account. If no charges are available, returns 0.

        Returns
        -------
        int
            The total number of completion tokens used, or 0 if unavailable.

        Example
        -------
        .. code-block:: python

            total_completion = provider.db_total_completion_tokens
            print(f"Completion tokens used: {total_completion}")
        """
        if not self.db_charges.exists():
            return 0
        return self.db_charges.aggregate(Sum("completion_tokens"))["completion_tokens__sum"]

    @property
    def db_total_total_tokens(self) -> int:
        """
        Get the total number of tokens used in the current prompt session.

        This property aggregates the `total_tokens` field across all charge records
        for the current prompt session and account. If no charges are available, returns 0.

        Returns
        -------
        int
            The total number of tokens used, or 0 if unavailable.

        Example
        -------
        .. code-block:: python

            total_tokens = provider.db_total_total_tokens
            print(f"Total tokens used: {total_tokens}")
        """
        if not self.db_charges.exists():
            return 0
        return self.db_charges.aggregate(Sum("total_tokens"))["total_tokens__sum"]

    @property
    def db_total_tokens(self) -> Optional[dict]:
        """
        Get a dictionary containing the total prompt, completion, and overall tokens used.

        This property returns a dictionary with the total number of prompt tokens,
        completion tokens, and overall tokens used in the current prompt session.
        The values are aggregated from all charge records for the session.

        Returns
        -------
        dict or None
            A dictionary with keys 'prompt_tokens', 'completion_tokens', and 'total_tokens',
            or None if no charge data is available.

        Example
        -------
        .. code-block:: python

            totals = provider.db_total_tokens
            if totals:
                print(f"Prompt: {totals['prompt_tokens']}, Completion: {totals['completion_tokens']}, Total: {totals['total_tokens']}")
        """
        return {
            _InternalKeys.PromptTokens: self.db_total_prompt_tokens,
            _InternalKeys.CompletionTokens: self.db_total_completion_tokens,
            _InternalKeys.TotalTokens: self.db_total_total_tokens,
        }

    @property
    def provider_name(self) -> Optional[str]:
        """
        Get the provider name associated with this provider model.

        This property returns the name of the provider that this model is configured to use.
        It is typically used to determine which provider's handler to invoke for prompt completions.

        Returns
        -------
        str or None
            The name of the provider, or None if not set.

        Example
        -------
        .. code-block:: python

            print(provider.provider_name)
        """
        if self.provider:
            return self.provider.name
        return None

    @property
    def provider(self) -> Optional[Provider]:
        """
        Get the Provider instance associated with this provider model.

        This property returns the `Provider` object that represents the provider
        configuration for this model. It is typically used to access provider-specific
        settings and information.

        Returns
        -------
        Provider or None
            The Provider instance associated with this model, or None if not set.

        Example
        -------
        .. code-block:: python

            provider_instance = provider.provider
            if provider_instance:
                print(provider_instance.name)
        """
        if self._provider is None and self._provider_name is not None:
            self._provider = Provider.objects.filter(is_active=True, name=self.provider_name).with_read_permission_for(self.user_profile.user).first()  # type: ignore
            if self._provider:
                logger.debug(
                    "%s.provider property loaded provider '%s' for user %s.",
                    self.formatted_class_name,
                    self._provider.name,
                    self.user_profile.user.username if self.user_profile and self.user_profile.user else "Unknown",
                )
            else:
                logger.warning(
                    "%s.provider property could not find an active provider with name '%s' for user %s.",
                    self.formatted_class_name,
                    self.provider_name,
                    self.user_profile.user.username if self.user_profile and self.user_profile.user else "Unknown",
                )
        return self._provider

    def db_refresh(self):
        """
        Refresh the provider instance and its cached database attributes.

        This method refreshes the prompt instance from the database and resets the cached
        charges queryset. Use this method to ensure the provider has the latest data
        after external changes to the prompt or related records.

        Example
        -------
        .. code-block:: python

            provider.db_refresh()
            # Now provider.db_charges and related properties are up to date
        """
        logger.debug("%s.db_refresh() called.", self.formatted_class_name)
        if self.prompt:
            # resets all lazy attributes to force reload on next access
            self.prompt = self.prompt

    def db_insert_chat_tool_call(self, *args, **kwargs):
        """
        Insert a prompt tool call record for the current prompt session.

        This method creates a new `PromptToolCall` record associated with the
        current prompt session. The insertion is performed asynchronously using
        a background task. If no prompt is set, the method returns without
        action.

        Parameters
        ----------
        plugin : Plugin, optional
            The plugin instance associated with the tool call (default: None).
        function_name : str, optional
            The name of the function called (default: None).
        function_args : dict or str, optional
            Arguments passed to the function (default: None).
        request : dict or str, optional
            The request payload (default: None).
        response : dict or str, optional
            The response payload (default: None).

        Example
        -------
        .. code-block:: python

            provider.db_insert_chat_tool_call(
                plugin=my_plugin,
                function_name="my_function",
                function_args={"arg1": 123},
                request={"input": "foo"},
                response={"output": "bar"}
            )
        """
        logger.debug(
            "%s.db_insert_chat_tool_call() called with args: %s kwargs: %s", self.formatted_class_name, args, kwargs
        )
        if not self.prompt:
            return
        prompt_id = self.prompt.id  # type: ignore
        plugin = kwargs.get("plugin", None)
        plugin_id = plugin.id if plugin else None
        function_name = kwargs.get("function_name", None)
        function_args = kwargs.get("function_args", None)
        request = kwargs.get("request", None)
        response = kwargs.get("response", None)
        create_prompt_tool_call_history.delay(prompt_id, plugin_id, function_name, function_args, request, response)

    def db_insert_chat_plugin_usage(self, *args, **kwargs):
        """
        Insert a prompt plugin usage record for the specified prompt session.

        This method creates a new `PromptPluginUsage` record associated with the given prompt session.
        The insertion is performed asynchronously using a background task. If no prompt is provided,
        the method logs a warning and returns without action.

        Parameters
        ----------
        prompt : Prompt, required
            The prompt instance for which to record plugin usage.
        plugin : Plugin, optional
            The plugin instance used in the prompt (default: None).
        input_text : str, optional
            The input text sent to the plugin (default: None).

        Example
        -------
        .. code-block:: python

            provider.db_insert_chat_plugin_usage(
                prompt=my_chat,
                plugin=my_plugin,
                input_text="search for weather"
            )
        """
        logger.debug(
            "%s.db_insert_chat_plugin_usage() called with args: %s kwargs: %s", self.formatted_class_name, args, kwargs
        )
        prompt = kwargs.get("prompt", None)
        if not prompt:
            logger.warning("db_insert_chat_plugin_usage() Prompt is required to create a prompt plugin usage record.")
            return
        prompt_id = prompt.id  # type: ignore
        plugin = kwargs.get("plugin", None)
        plugin_id = plugin.id if plugin else None
        input_text = kwargs.get("input_text", None)
        create_prompt_plugin_usage.delay(prompt_id=prompt_id, plugin_id=plugin_id, input_text=input_text)

    def db_insert_charge(
        self,
        resource_locators: list[str],
        charge_type: str,
        completion_tokens: int,
        prompt_tokens: int,
        total_tokens: int,
    ):
        """
        Insert a new charge record for the current account and prompt session.

        This method asynchronously creates a new `Charge` record associated with the current account, user, and prompt session. It is typically used to persist billing or usage information for a model completion or related operation.

        Parameters
        ----------
        resource_locators : list[str]
            A list of resource locators associated with the charge (e.g., provider, user profile).
        charge_type : str
            The type of charge (e.g., "completion", "plugin").
        completion_tokens : int
            The number of completion tokens used.
        prompt_tokens : int
            The number of prompt tokens used.
        total_tokens : int
            The total number of tokens used.
        model : str
            The model name or identifier (e.g., "gpt-4").
        reference : str
            An external reference or identifier for the charge (e.g., request ID).

        Raises
        ------
        SmarterValueError
            If the account or prompt is not set.

        Example
        -------
        .. code-block:: python

            provider.db_insert_charge(
                resource_locators=["provider-xyz", "user-profile-abc"],
                charge_type="completion",
                completion_tokens=42,
                prompt_tokens=58,
                total_tokens=100,
                model="gpt-4",
                reference="req-12345"
            )
        """
        logger.debug(
            "%s.db_insert_charge() called with resource_locators: %s, charge_type: %s, completion_tokens: %d, prompt_tokens: %d, total_tokens: %d",
            self.formatted_class_name,
            resource_locators,
            charge_type,
            completion_tokens,
            prompt_tokens,
            total_tokens,
        )
        if not isinstance(self.user_profile, UserProfile):
            raise SmarterValueError("Account is required to create a charge record.")
        if not resource_locators:
            raise SmarterValueError("Resource locators are required to create a charge record.")
        if not self.prompt:
            raise SmarterValueError("Prompt is required to create a charge record.")

        resource_locators.append(self.user_profile.record_locator)
        resource_locators.append(self.user_profile.account.record_locator)

        for resource_locator in resource_locators:
            create_charge.delay(
                resource_locator=resource_locator,
                charge_type=charge_type,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )
        charge_authorization(resource_locators, charge_type)  # type: ignore


__all__ = ["ChatDbMixin"]
