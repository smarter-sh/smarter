# pylint: disable=C0115
"""PromptHelper for the prompt app."""

from functools import cached_property
from typing import Any, Optional, Union

from django.db import models
from django.db.utils import IntegrityError
from django.http import HttpRequest
from rest_framework import serializers

from smarter.apps.llm_client.models import LLMClient, get_cached_llm_client_by_request
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.lib import logging
from smarter.lib.cache import lazy_cache as cache
from smarter.lib.django import waffle
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .prompt import Prompt
from .prompt_history import PromptHistory
from .prompt_plugin_usage import PromptPluginUsage
from .prompt_tool_call import PromptToolCall


# pylint: disable=W0613
def should_log_verbose(level) -> bool:
    return smarter_settings.verbose_logging


logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING])
logger_verbose = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING], condition_func=should_log_verbose
)


# --------------------------------------------------------------------------------
# Mini Serializers - only used by PromptHelper.
# --------------------------------------------------------------------------------
class PromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prompt
        fields = "__all__"


class PromptToolCallSerializer(serializers.ModelSerializer):
    """Serializer for the PromptToolCall model."""

    prompt = PromptSerializer(read_only=True)

    class Meta:
        model = PromptToolCall
        fields = "__all__"


class PromptPluginUsageSerializer(serializers.ModelSerializer):
    """Serializer for the PromptPluginUsage model."""

    prompt = PromptSerializer(read_only=True)

    class Meta:
        model = PromptPluginUsage
        fields = "__all__"


class PromptHelper(SmarterRequestMixin):
    """
    Helper class for working with :class:`Prompt` objects.

    This class provides methods for creating and retrieving :class:`Prompt` objects,
    as well as managing the cache for prompt sessions. It is designed to simplify
    the process of interacting with prompt-related data and to ensure consistent
    handling of prompt sessions, llm_clients, and associated metadata.

    **Features**

    - Abstracts the logic for creating and retrieving prompt sessions.
    - Manages caching of prompt objects to improve performance and reduce database queries.
    - Provides access to related prompt history, tool calls, and plugin usage.
    - Integrates with Django's request and session handling.
    - Ensures that prompt sessions are always associated with a valid :class:`LLMClient` and :class:`Account`.

    **Usage**

    Typically, this class is instantiated with a Django :class:`HttpRequest` object and a session key.
    Optionally, a :class:`LLMClient` instance can be provided to associate the prompt session with a specific llm_client.

    Example
    -------
    .. code-block:: python

        helper = PromptHelper(request, session_key)
        if helper.ready:
            prompt = helper.prompt
            llm_client = helper.llm_client
            history = helper.history

    :param request: The Django HttpRequest object for the current session.
    :type request: django.http.HttpRequest
    :param session_key: The session key identifying the prompt session.
    :type session_key: Optional[str]
    :param llm_client: An optional LLMClient instance to associate with the prompt session.
    :type llm_client: Optional[LLMClient]
    :param args: Additional positional arguments.
    :param kwargs: Additional keyword arguments.

    :raises SmarterValueError: If neither a session key nor a LLMClient instance is provided.
    :raises SmarterConfigurationError: If there is an error creating a new Prompt object.

    .. note::
        This class is intended for internal use within the Smarter platform and
        should not be used directly in user-facing code without proper validation.

    .. todo::
        - Remove the session_key parameter and rely solely on the LLMClient instance for prompt session management.

    .. seealso::
        - :class:`smarter.apps.llm_client.models.LLMClient`
        - :class:`smarter.apps.account.models.Account`
        - :class:`smarter.apps.prompt.models.Prompt`
        - :class:`smarter.lib.django.request.SmarterRequestMixin`
    """

    _chat: Optional[Prompt] = None
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
        :param session_key: The session key identifying the prompt session.
        :type session_key: Optional[str]
        :param llm_client: An optional LLMClient instance to associate with the prompt session.
        :type llm_client: Optional[LLMClient]
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :raises SmarterValueError: If neither a session key nor a LLMClient instance is provided.
        :raises SmarterConfigurationError: If there is an error creating a new Prompt object.
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

            # rerun the ready status check to ensure that the account is authorized and ready.
            self._am_ready = False
            # pylint: disable=W0104
            self.am_ready

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
            "%s.__init__() - %s with session_key: %s, prompt: %s",
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

        This property returns ``True`` if the prompt instance is available and all required
        attributes are set, otherwise returns ``False``. It is useful for determining
        whether the PromptHelper is fully initialized and ready for prompt operations.

        :returns: ``True`` if the PromptHelper is ready to use, otherwise ``False``.
        :rtype: bool
        """
        return bool(super().ready) and bool(self._session_key) and bool(self._chat) and bool(self._llm_client)

    def to_json(self) -> dict[str, Any]:
        """
        Convert the PromptHelper instance to a JSON serializable dictionary.

        This method returns a dictionary representation of the PromptHelper instance,
        including key metadata and related objects such as the prompt, llm_client, prompt history,
        and a unique client string.

        :returns: A dictionary containing the serialized state of the PromptHelper.
        :rtype: dict[str, Any]
        """
        return self.sorted_dict(
            {
                **super().to_json(),
                "ready": self.ready,
                "session_key": self.session_key,
                "prompt": self.prompt.id if self.prompt else None,  # type: ignore[return]
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
    def prompt(self):
        """
        Get the prompt instance for the current request.

        :returns: The Prompt instance associated with the current session.
        :rtype: Prompt
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
    def prompt_history(self) -> Union[models.QuerySet, list]:
        """
        Get the most recent prompt history for the current prompt session.

        :returns: The most recent PromptHistory instance's prompt_history field, or an empty list if none found.
        :rtype: Union[models.QuerySet, list]
        """
        rec = PromptHistory.objects.filter(prompt=self.prompt).order_by("-created_at").first()
        return rec.prompt_history if rec else []

    @property
    def prompt_tool_call(self) -> Union[models.QuerySet, list]:
        """
        Get the most recent prompt tool call history for the current prompt session.

        :returns: A queryset of PromptToolCall instances for the current prompt session, ordered by creation date.
        :rtype: Union[models.QuerySet, list]
        """
        if self._prompt_tool_call:
            return self._prompt_tool_call
        self._prompt_tool_call = PromptToolCall.objects.filter(prompt=self.prompt).order_by("-created_at") or []
        return self._prompt_tool_call

    @property
    def prompt_plugin_usage(self) -> Union[models.QuerySet, list]:
        """
        Get the most recent prompt plugin usage history for the current prompt session.

        :returns: A queryset of PromptPluginUsage instances for the current prompt session, ordered by creation date.
        :rtype: Union[models.QuerySet, list]
        """
        if self._prompt_plugin_usage:
            return self._prompt_plugin_usage
        self._prompt_plugin_usage = PromptPluginUsage.objects.filter(prompt=self.prompt).order_by("-created_at") or []
        return self._prompt_plugin_usage

    @property
    def history(self) -> dict:
        """
        Serialize the most recent logged history output for the prompt session.

        :returns: A dictionary containing serialized prompt, prompt history, tool calls, and plugin usage.
        :rtype: dict
        """
        if self._history:
            return self._history
        chat_serializer = PromptSerializer(self.prompt)
        prompt_tool_call_serializer = PromptToolCallSerializer(self.prompt_tool_call, many=True)
        prompt_plugin_usage_serializer = PromptPluginUsageSerializer(self.prompt_plugin_usage, many=True)
        self._history = {
            "prompt": chat_serializer.data,
            "prompt_history": self.prompt_history,
            "prompt_tool_call_history": prompt_tool_call_serializer.data,
            "prompt_plugin_usage_history": prompt_plugin_usage_serializer.data,
            # these two will be added upstream.
            "llm_client_request_history": None,  # LLMClientRequests
        }
        return self._history

    def get_cached_chat(self) -> Optional[Prompt]:
        """
        Get the prompt instance for the current request.

        This method retrieves the Prompt instance associated with the current session key
        from the cache. If the Prompt instance is not found in the cache, it attempts to
        retrieve it from the database. If it still cannot be found, a new Prompt instance
        is created using the provided LLMClient and request metadata.

        :returns: The Prompt instance associated with the current session, or ``None`` if not found.
        :rtype: Optional[Prompt]
        """
        if not self.smarter_request:
            logger.error("%s - request object is required for PromptHelper.", self.formatted_class_name)
            return None

        prompt: Prompt = cache.get(self.session_key)  # type: ignore[assignment]
        if prompt:
            logger_verbose.debug(
                "%s - retrieved cached Prompt: %s session_key: %s",
                self.formatted_class_name,
                prompt,
                prompt.session_key,
            )
            return prompt

        if self.session_key:
            try:
                prompt = Prompt.objects.get(session_key=self.session_key)
                logger_verbose.debug(
                    "%s - retrieved Prompt instance: %s session_key: %s",
                    self.formatted_class_name,
                    prompt,
                    prompt.session_key,
                )
            except Prompt.DoesNotExist:
                pass

        if not prompt:
            if not self.llm_client:
                raise SmarterValueError(
                    f"{self.formatted_class_name} LLMClient instance is required for creating a Prompt object."
                )

            try:
                # modify the unit test server URL
                # to a more Django friendly URL.
                django_friendly_url = self.url or ""
                django_friendly_url = django_friendly_url.replace("http://testserver/", "http://testserver.local/")
                prompt = Prompt.objects.create(
                    session_key=self.session_key,
                    user_profile=self.user_profile,
                    llm_client=self.llm_client,
                    ip_address=self.ip_address,
                    user_agent=self.user_agent,
                    url=django_friendly_url,
                )
            except IntegrityError as e:
                raise SmarterConfigurationError(f"{self.formatted_class_name} - IntegrityError: {str(e)}") from e

        cache.set(key=self.session_key, value=prompt, timeout=smarter_settings.chat_cache_expiration or 300)
        if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
            logger_verbose.debug(
                "%s - cached prompt instance: %s session_key: %s", self.formatted_class_name, prompt, prompt.session_key
            )

        if not prompt.llm_client:
            raise ValueError(f"{self.formatted_class_name} LLMClient instance is required for Prompt object.")

        return prompt
