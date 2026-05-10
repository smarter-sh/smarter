"""All models for the OpenAI Function Calling API app."""

from functools import cached_property
from typing import Any, Optional
from urllib.parse import ParseResult

from django.http import HttpRequest

from smarter.apps.account.models import (
    Account,
    UserProfile,
)
from smarter.apps.account.utils import (
    account_number_from_url,
    get_cached_admin_user_for_account,
    smarter_cached_objects,
)
from smarter.apps.provider.models import Provider
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import (
    formatted_text,
    formatted_text_green,
    formatted_text_red,
)
from smarter.lib import logging
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .chatbot import ChatBot
from .chatbot_api_key import ChatBotAPIKey
from .chatbot_custom_domain import ChatBotCustomDomain
from .chatbot_plugin import ChatBotPlugin
from .chatbot_requests import ChatBotRequests

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.CHATBOT_LOGGING])
chatbot_helper_logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.CHATBOT_HELPER_LOGGING])


class ChatBotHelper(SmarterRequestMixin):
    """
    Provides a mapping between URLs and their corresponding ChatBot models,
    abstracting URL parsing logic for reuse across the codebase.

    This helper class is designed to centralize and standardize the logic
    required to resolve a ChatBot instance from a given URL or request context.
    It is intended for use in various locations, including within this module,
    Django middleware, and view logic.

    The class also implements caching of ChatBot objects for specific URLs,
    reducing redundant parsing and database queries for repeated requests.

    **Supported URL Patterns**

    The following are examples of valid URLs that this helper can process:

    - **Authentication Optional URLs:**
        - ``https://example-username.3141-5926-5359.alpha.api.example.com/``
        - ``https://example-username.3141-5926-5359.alpha.api.example.com/config/``

    - **Authenticated URLs:**
        - ``https://alpha.api.example-username.com/smarter/example/``
        - ``https://example-username.smarter.sh/chatbot/``
        - ``https://alpha.api.example-username.com/workbench/1/``
        - ``https://alpha.api.example-username.com/workbench/example/``

    - **Legacy (pre v0.12) URLs:**
        - ``https://alpha.api.example-username.com/chatbots/1/``
        - ``https://alpha.api.example-username.com/chatbots/example/``

    where for ``example-username``,  ``example`` is the ChatBot name,
    ``username`` is the Account Username, and ``3141-5926-5359`` is the
    Account Number.

    **Features**

    - Abstracts and encapsulates URL parsing and ChatBot resolution logic.
    - Provides a consistent interface for retrieving ChatBot instances from URLs.
    - Caches ChatBot objects to avoid redundant lookups.
    - Supports both authenticated and unauthenticated URL patterns.
    - Handles legacy URL formats for backward compatibility.

    **Usage**

    This class is typically instantiated with a Django ``HttpRequest`` object.
    It can then be used to access the resolved ChatBot instance and related
    metadata, such as the associated account, chatbot ID, and custom domain.

    Example::

        helper = ChatBotHelper(request)
        chatbot = helper.chatbot
        if helper.is_valid:
            # Proceed with chatbot logic

    :param request: The Django HttpRequest object containing the URL and user context.
    :type request: django.http.HttpRequest
    :param args: Additional positional arguments.
    :param kwargs: Additional keyword arguments, such as 'chatbot', 'chatbot_custom_domain', etc.

    :raises SmarterConfigurationError: If the helper cannot resolve a valid ChatBot instance.

    .. note::
        This class is intended for internal use within the Smarter platform and
        should not be used directly in user-facing code without proper validation.
    """

    __slots__ = (
        "_chatbot",
        "_chatbot_custom_domain",
        "_chatbot_requests",
        "_chatbot_id",
        "_name",
        "_is_chatbothelper_ready",
    )

    def __init__(self, request: HttpRequest, *args, **kwargs):
        """
        Initializes the ChatBotHelper instance.

        :param request: The Django HttpRequest object.
        :type request: django.http.HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        """
        self._chatbot = None
        self._chatbot_custom_domain = None
        self._chatbot_requests = None
        self._chatbot_id = None
        self._name = None
        self._is_chatbothelper_ready: bool = False

        chatbot_helper_logger.debug(
            "%s.__init__() called with url: %s args: %s, kwargs: %s",
            self.formatted_class_name,
            request.build_absolute_uri() if request else None,
            args,
            kwargs,
        )
        self._chatbot: Optional[ChatBot] = kwargs.get("chatbot")
        if isinstance(self._chatbot, ChatBot):
            chatbot_helper_logger.debug(
                "%s.__init__() received ChatBot: %s",
                self.formatted_class_name,
                str(self._chatbot),
            )
        self._chatbot_id: Optional[int] = kwargs.get("chatbot_id")
        if isinstance(self._chatbot_id, int):
            chatbot_helper_logger.debug(
                "%s.__init__() received chatbot_id: %s",
                self.formatted_class_name,
                str(self._chatbot_id),
            )
        self._name: Optional[str] = kwargs.get("name")
        if isinstance(self._name, str):
            chatbot_helper_logger.debug(
                "%s.__init__() received name: %s",
                self.formatted_class_name,
                str(self._name),
            )

        self._chatbot_custom_domain: Optional[ChatBotCustomDomain] = kwargs.get("chatbot_custom_domain")
        if isinstance(self._chatbot_custom_domain, ChatBotCustomDomain):
            chatbot_helper_logger.debug(
                "%s.__init__() received ChatBotCustomDomain: %s",
                self.formatted_class_name,
                str(self._chatbot_custom_domain),
            )
        self._chatbot_requests: Optional[ChatBotRequests] = kwargs.get("chatbot_requests")
        if isinstance(self._chatbot_requests, ChatBotRequests):
            chatbot_helper_logger.debug(
                "%s.__init__() received ChatBotRequests: %s",
                self.formatted_class_name,
                str(self._chatbot_requests),
            )

        # initializations that depend on the superclass
        super().__init__(request, *args, **kwargs)
        chatbot_helper_logger.debug("%s.__init__() completed super().__init__()", self.formatted_class_name)
        self._chatbot_id = self._chatbot_id or self.smarter_request_chatbot_id
        self._name = self._name or self.smarter_request_chatbot_name

        if self.is_chatbot:
            if not isinstance(self.chatbot, ChatBot):
                if self.user_profile and self._name:
                    try:
                        self.chatbot = ChatBot.get_cached_object(name=self._name, user_profile=self.user_profile)
                    except ChatBot.DoesNotExist:
                        chatbot_helper_logger.warning(
                            "%s.__init__() could not find ChatBot with name=%s and user_profile=%s",
                            self.formatted_class_name,
                            self._name,
                            self.user_profile,
                        )

            if not isinstance(self._chatbot, ChatBot):
                chatbot_helper_logger.warning(
                    "%s.__init__() did not find a ChatBot for url=%s, name=%s, chatbot_id=%s, user_profile=%s",
                    self.formatted_class_name,
                    self.url,
                    self.name,
                    self.chatbot_id,
                    self.user_profile,
                )

        msg = f"{self.formatted_class_name}.__init__() is {self.chatbothelper_ready_state} - {self.chatbot if self.chatbot else 'ChatBot not initialized'} - {self.user_profile if self.user_profile else 'UserProfile not initialized'}"
        if self.ready:
            chatbot_helper_logger.debug(msg)
            chatbot_helper_logger.debug(
                "%s.__init__() initialized with url=%s, name=%s, chatbot_id=%s, user=%s, user_profile=%s, session_key=%s",
                self.formatted_class_name,
                self.url if self.url else "undefined",
                self.name,
                self.chatbot_id,
                self.user,
                self.user_profile,
                self.session_key,
            )
        else:
            chatbot_helper_logger.error(msg)

    def __str__(self):
        return str(self.chatbot) if self._chatbot else "undefined"

    @cached_property
    def formatted_class_name(self) -> str:
        """
        Get the formatted class name for this instance of ChatBotHelper.

        :returns: The formatted class name as a string, including the parent class name.
        :rtype: str

        This property returns a string representation of the class name,
        formatted to include the parent class's formatted name and the
        ``ChatBotHelper`` class. This is useful for logging and debugging
        purposes, as it provides a clear and consistent identifier for
        instances of this helper class.

        Example
        -------
        >>> helper = ChatBotHelper(request)
        >>> helper.formatted_class_name
        'smarter.apps.chatbot.models.ChatBotHelper()'
        """
        return formatted_text(f"{__name__}.{ChatBotHelper.__name__}()")

    @cached_property
    def account(self) -> Optional[Account]:
        """
        Return the associated :class:`Account` for this ChatBotHelper instance,
        optionally overriding the default account based on the account number
        parsed from the URL, if available.

        If the URL contains an account number (for example,
        ``http://education.3141-5926-5359.api.localhost:9357/config/``),
        this method will attempt to retrieve and return the corresponding
        cached Account object. If no account number is found in the URL,
        the default account from the superclass is returned.

        :returns: The resolved :class:`Account` instance, or ``None`` if not found.
        :rtype: Optional[Account]
        """
        account_number = account_number_from_url(self._url)  # type: ignore[arg-type]
        if account_number:
            chatbot_helper_logger.debug("overriding account with account_number from named url: %s", self.url)
            return Account.get_cached_object(account_number=account_number)

        # from the super()
        return self._account

    @property
    def chatbot_id(self) -> Optional[int]:
        """
        Returns the :attr:`ChatBot.id` for this ChatBotHelper instance.

        This property attempts to resolve the ChatBot's unique integer ID using several strategies:

        1. If a chatbot ID was provided at initialization, it is returned immediately.
        2. If a ChatBot object is already cached, its ID is returned.
        3. If the parent :class:`SmarterRequestMixin` provides a chatbot ID (e.g., parsed from the URL), it is used.
        4. If both a chatbot name and account are available, attempts to resolve and cache the ChatBot object and its ID.

        :returns: The resolved ChatBot ID, or ``None`` if not found.
        :rtype: Optional[int]
        """
        # check for a value passed in
        if self._chatbot_id:
            return self._chatbot_id

        # check for a chatbot object
        if self._chatbot:
            self._chatbot_id = self.chatbot.id  # type: ignore[return-value]
            return self._chatbot_id

        # check SmarterRequestMixin for a chatbot_id derived from the  url
        self._chatbot_id = super().smarter_request_chatbot_id
        if self._chatbot_id:
            return self._chatbot_id

        if self.chatbot_name and self.user_profile:
            self.chatbot = ChatBot.get_cached_object(name=self.chatbot_name, user_profile=self.user_profile)
            chatbot_helper_logger.debug(
                "chatbot_id() initialized self.chatbot_id=%s from name=%s and account=%s",
                self._chatbot_id,
                self.chatbot_name,
                self.account,
            )
            return self._chatbot_id

        return self._chatbot_id

    @chatbot_id.setter
    def chatbot_id(self, chatbot_id: int):
        self._chatbot_id = chatbot_id
        chatbot = ChatBot.get_cached_object(pk=chatbot_id)
        if chatbot and chatbot.user_profile.cached_account != self.account:
            raise SmarterValueError("ChatBotHelper.chatbot_id setter: ChatBot's Account does not match self.account")
        self.chatbot = chatbot
        if self._chatbot:
            chatbot_helper_logger.debug(
                "@chatbot_id.setter initialized self.chatbot_id=%s from chatbot_id=%s", self._chatbot_id, chatbot_id
            )

    @property
    def chatbot_name(self) -> Optional[str]:
        """
        Returns the ChatBot.name for the ChatBotHelper.
        """
        return self.name

    @property
    def name(self) -> Optional[str]:
        """
        Returns the name of the chatbot.

        This property attempts to resolve the chatbot's name using several strategies, in order of precedence:

        1. ``self._name``: The name assigned during initialization, if available.
        2. ``self.chatbot.name``: The name attribute of the resolved ChatBot instance, if present.
        3. ``self.subdomain``: If the URL is a named chatbot URL (i.e., ``is_chatbot_named_url`` is True), the subdomain is used as the name.
        4. Path slug: If the URL is a sandbox chatbot URL (i.e., ``is_chatbot_sandbox_url`` is True), the path slug is used as the name.

        :returns: The resolved chatbot name, or ``None`` if not found.
        :rtype: Optional[str]
        """
        if self._chatbot:
            self._name = self._chatbot.name

        return self._name

    @property
    def rfc1034_compliant_name(self) -> Optional[str]:
        """
        Returns a URL-friendly name for the chatbot.

        This is a convenience property that returns a RFC 1034 compliant name for the chatbot.

        Examples
        --------
        .. code-block:: python

            self.name  # 'Example ChatBot 1'
            self.rfc1034_compliant_name  # 'example-chatbot-1'

        :returns: The RFC 1034 compliant name for the chatbot, or ``None`` if not available.
        :rtype: Optional[str]
        """
        if self._chatbot:
            return self._chatbot.rfc1034_compliant_name
        return None

    @cached_property
    def is_chatbothelper_ready(self) -> bool:
        """
        Returns ``True`` if the ChatBotHelper is ready to be used.

        This is a convenience property that checks if the ChatBotHelper
        is initialized and has a valid :class:`ChatBot` instance.

        :returns: ``True`` if the helper is initialized and has a valid ChatBot, otherwise ``False``.
        :rtype: bool
        """
        if self._is_chatbothelper_ready:
            return True
        logger_prefix = f"{self.formatted_class_name}.is_chatbothelper_ready()"

        if isinstance(self._chatbot, ChatBot):
            chatbot_helper_logger.debug(
                "%s returning true because chatbot is initialized: %s",
                logger_prefix,
                self._chatbot,
            )
            self._is_chatbothelper_ready = True
            return self._is_chatbothelper_ready

        if self.chatbot_custom_domain:
            chatbot_helper_logger.debug(
                "%s chatbot_custom_domain is set but ChatBotHelpler is not confirmed to be ready.",
                logger_prefix,
            )

        if not self.is_chatbot:
            chatbot_helper_logger.debug(
                "%s returning false because is_chatbot is false",
                logger_prefix,
            )
            return False
        else:
            chatbot_helper_logger.debug(
                "%s confirmed URL is a chatbot URL. url=%s",
                logger_prefix,
                self._url,
            )
        if not self.user or not self.user.is_authenticated:
            chatbot_helper_logger.warning(
                "%s returning false because called with unauthenticated request",
                logger_prefix,
            )
            return False
        else:
            chatbot_helper_logger.debug(
                "%s confirmed request user is authenticated: %s",
                logger_prefix,
                self.user.username,
            )
        if not self.account:
            chatbot_helper_logger.warning("%s returning false because called with no account", logger_prefix)
            return False
        else:
            chatbot_helper_logger.debug(
                "%s confirmed account is assigned: %s",
                logger_prefix,
                self.account,
            )
        if not isinstance(self.name, str):
            chatbot_helper_logger.warning(
                "%s returning false because did not find a name for the chatbot.", logger_prefix
            )
            return False
        else:
            chatbot_helper_logger.debug(
                "%s confirmed chatbot name is assigned: %s",
                logger_prefix,
                self.name,
            )
        if not isinstance(self._chatbot, ChatBot):
            chatbot_helper_logger.debug(
                "%s returning false because ChatBot is not initialized.",
                logger_prefix,
            )
            return False
        else:
            chatbot_helper_logger.debug(
                "%s confirmed ChatBot is initialized: %s",
                logger_prefix,
                self._chatbot,
            )
            self._is_chatbothelper_ready = True
            return self._is_chatbothelper_ready

    @property
    def chatbothelper_ready_state(self) -> str:
        """
        Returns a formatted string indicating whether the ChatBotHelper is ready.

        :return: A string indicating whether the ChatBotHelper is ready or not.
        """
        return formatted_text_green("Ready") if self.is_chatbothelper_ready else formatted_text_red("Not Ready")

    @property
    def ready(self) -> bool:
        """
        Returns ``True`` if the ChatBotHelper and its ChatBot are ready to be used.
        This property checks both the readiness of the ChatBotHelper itself and the readiness
        of the underlying ChatBot instance.

        :returns: ``True`` if both the helper and ChatBot are ready, otherwise ``False``.
        :rtype: bool
        """
        # there is a scenario where the SmarterRequestMixin is not ready but the ChatBotHelper is.
        if self.is_chatbothelper_ready and self.user_profile and not super().ready:
            chatbot_helper_logger.debug(
                "%s.ready() returning true because ChatBotHelper is ready even though SmarterRequestMixin is not ready",
                self.formatted_class_name,
            )
            return True
        if not super().ready:
            chatbot_helper_logger.debug(
                "%s.ready() returning false because SmarterRequestMixin is not ready", self.formatted_class_name
            )
            return False

        return self.is_chatbothelper_ready

    def to_json(self) -> dict[str, Any]:
        """
        Serialize the ChatBotHelper to a dictionary.

        This method returns a dictionary representation of the ChatBotHelper instance,
        including key metadata and related objects such as the chatbot, account, and custom domain.

        :returns: A dictionary containing the serialized state of the ChatBotHelper.
        :rtype: dict[str, Any]
        """
        # pylint: disable=C0415
        from smarter.apps.chatbot.serializers import (
            ChatBotCustomDomainSerializer,
            ChatBotSerializer,
        )

        return self.sorted_dict(
            {
                "ready": self.ready,
                "name": self.name,
                "api_host": self.api_host,
                "chatbot_id": self.chatbot_id,
                "chatbot_name": self.chatbot_name,
                "chatbot_custom_domain": (
                    ChatBotCustomDomainSerializer(self.chatbot_custom_domain) if self.chatbot_custom_domain else None
                ),
                "environment_api_domain": smarter_settings.environment_api_domain,
                "is_custom_domain": self.is_custom_domain,
                "is_deployed": self.is_deployed,
                "is_authentication_required": self.is_authentication_required,
                "is_chatbothelper_ready": self.is_chatbothelper_ready,
                "rfc1034_compliant_name": self.rfc1034_compliant_name,
                "chatbot": ChatBotSerializer(self.chatbot).data if self.chatbot else None,
                "url": self.url,
                **super().to_json(),
            }
        )

    @cached_property
    def api_host(self) -> Optional[str]:
        """
        Returns the API host for a ChatBot API URL.

        This property extracts and returns the API host component from the chatbot URL,
        supporting named, sandbox, and custom domain URLs.

        Examples
        --------
        Named URL:
            - ``https://hr.3141-5926-5359.alpha.api.example.com/chatbot/``
              returns ``'alpha.api.example.com'``

        Sandbox URL:
            - ``http://api.localhost:9357/api/v1/chatbots/1/chat/``
              returns ``'api.localhost:9357'``

        Custom domain URL:
            - ``https://hr.smarter.sh/chatbot/``
              returns ``'hr.smarter.sh'``

        :returns: The API host as a string, or ``None`` if not found.
        :rtype: Optional[str]
        """
        if not self.smarter_request:
            return None
        if not self.qualified_request:
            return None
        if self.is_smarter_api and isinstance(self._url, ParseResult):
            return self._url.netloc
        if self.is_custom_domain and isinstance(self._url, ParseResult):
            # example: hr.bots.example.com
            return self._url.netloc
        return smarter_settings.environment_api_domain

    @property
    def is_deployed(self) -> bool:
        return self.chatbot.deployed if self.chatbot else False  # type: ignore[return-value]

    @cached_property
    def is_authentication_required(self) -> bool:
        """
        Determines if authentication is required to access the ChatBot.

        :returns: ``True`` if authentication is required, otherwise ``False``.
        :rtype: bool
        """
        if self.is_chatbot_sandbox_url:
            return True

        if not self.chatbot:
            return False
        chatbotapikeys = ChatBotAPIKey.get_cached_objects(chatbot=self.chatbot)
        if chatbotapikeys.filter(api_key__is_active=True).exists():
            return True
        return False

    @property
    def chatbot(self) -> Optional[ChatBot]:
        """
        Returns a lazy instance of the ChatBot.

        Examples
        --------
        - https://hr.3141-5926-5359.alpha.api.example.com/chatbot/
          returns ChatBot(name='hr', account=Account(...))

        :returns: The ChatBot instance, or ``None`` if not found.
        :rtype: Optional[ChatBot]
        """
        if self._chatbot:
            return self._chatbot

        # cheapest possibility
        if self._chatbot_id:
            self.chatbot = ChatBot.get_cached_object(pk=self._chatbot_id)
            chatbot_helper_logger.debug("initialized chatbot %s from chatbot_id %s", self._chatbot, self.chatbot_id)
            return self._chatbot

        # our expected case
        if self.user_profile and self.name:
            try:
                self.chatbot = ChatBot.get_cached_object(name=self.name, user_profile=self.user_profile)
                chatbot_helper_logger.debug(
                    "initialized chatbot %s from account %s and name %s", self._chatbot, self.account, self.name
                )
                return self._chatbot
            except ChatBot.DoesNotExist:
                chatbot_helper_logger.error(
                    "%s.chatbot() did not find chatbot for %s name: %s",
                    self.formatted_class_name,
                    self._user_profile,
                    self.name,
                )

        return self._chatbot

    @chatbot.setter
    def chatbot(self, chatbot: ChatBot):
        """
        Sets the ChatBot instance for this ChatBotHelper.
        """
        self._chatbot = chatbot
        if self._chatbot:
            self._chatbot_id = self._chatbot.id  # type: ignore[assignment]
            self._name = self._chatbot.name
            chatbot_helper_logger.debug(
                "@chatbot.setter initialized self.chatbot_id=%s and self.name=%s from chatbot",
                self._chatbot_id,
                self._name,
            )
        else:
            self._chatbot_id = None
            self._name = None
            chatbot_helper_logger.debug("@chatbot.setter cleared self.chatbot_id and self.name because chatbot is None")
        if hasattr(self, "is_chatbothelper_ready"):
            del self.is_chatbothelper_ready

    @cached_property
    def provider(self) -> Optional[Provider]:
        """
        Returns the Provider associated with the ChatBot.

        :returns: The Provider instance, or ``None`` if not found.
        :rtype: Optional[Provider]
        """
        if not self.chatbot:
            return None
        try:
            # FIX NOTE: self.chatbot.provider should be a foreign key to Provider.
            return Provider.get_cached_object(name=self.chatbot.provider, account=self.account)  # type: ignore[return-value]
        except Provider.DoesNotExist:
            return None

    @property
    def chatbot_plugins_list(self) -> list[ChatBotPlugin]:
        """
        Returns a list of ChatBotPlugin instances associated with the ChatBot.

        :returns: A list of ChatBotPlugin instances.
        :rtype: list[ChatBotPlugin]
        """
        if not self.chatbot:
            return []
        return list(ChatBotPlugin.get_cached_objects(chatbot=self.chatbot))

    @cached_property
    def chatbot_plugins_list_str(self) -> str:
        """
        Returns a comma-separated string of ChatBotPlugin names associated with the ChatBot.

        :returns: A comma-separated string of ChatBotPlugin names.
        :rtype: str
        """
        plugins = self.chatbot_plugins_list
        return ", ".join(
            str(plugin.plugin_meta.name) + " (" + str(plugin.plugin_meta.user_profile) + ")" for plugin in plugins
        )

    @property
    def is_custom_domain(self) -> bool:
        """
        Returns ``True`` if the ChatBot is using a custom domain.

        :returns: ``True`` if a custom domain is configured, otherwise ``False``.
        :rtype: bool
        """
        return self.chatbot_custom_domain is not None

    @property
    def chatbot_custom_domain(self) -> Optional[ChatBotCustomDomain]:
        """
        Returns a lazy instance of the ChatBotCustomDomain.

        Examples
        --------
        - ``https://hr.smarter.sh/chatbot/``
          returns ``ChatBotCustomDomain(domain_name='smarter.sh')``

        :returns: The ChatBotCustomDomain instance, or ``None`` if not found.
        :rtype: Optional[ChatBotCustomDomain]
        """
        if self._chatbot_custom_domain:
            return self._chatbot_custom_domain

        try:
            self._chatbot_custom_domain = ChatBotCustomDomain.objects.get(
                user_profile=self.user_profile, domain_name=self.root_domain
            )
            logger.debug(
                "%s.chatbot_custom_domain() found ChatBotCustomDomain for root domain: %s %s",
                self.formatted_class_name,
                self.root_domain,
                self.user_profile,
            )
        except ChatBotCustomDomain.DoesNotExist:
            if not self.account:
                logger.warning(
                    "%s.chatbot_custom_domain() cannot lookup ChatBotCustomDomain for rootdomain: %s because account is None",
                    self.formatted_class_name,
                    self.root_domain,
                )
                return None
            account_admin = get_cached_admin_user_for_account(account=self.account)  # type: ignore[arg-type]
            account_admin_user_profile = UserProfile.get_cached_object(user=account_admin)  # type: ignore[arg-type]

            try:
                self._chatbot_custom_domain = ChatBotCustomDomain.objects.get(
                    user_profile=account_admin_user_profile,
                    domain_name=self.root_domain,
                )
                logger.debug(
                    "%s.chatbot_custom_domain() found ChatBotCustomDomain for rootdomain: %s under account admin user_profile id %s",
                    self.formatted_class_name,
                    self.root_domain,
                    account_admin_user_profile,
                )
            except ChatBotCustomDomain.DoesNotExist:
                try:
                    self._chatbot_custom_domain = ChatBotCustomDomain.objects.get(
                        user_profile=smarter_cached_objects.smarter_admin_user_profile,
                        domain_name=self.root_domain,
                    )
                    logger.debug(
                        "%s.chatbot_custom_domain() found ChatBotCustomDomain for rootdomain: %s under smarter platform admin user_profile id %s",
                        self.formatted_class_name,
                        self.root_domain,
                        smarter_cached_objects.smarter_admin_user_profile,
                    )
                except ChatBotCustomDomain.DoesNotExist:
                    pass

        if not self._chatbot_custom_domain:
            logger.debug(
                "%s.chatbot_custom_domain() did not find ChatBotCustomDomain for rootdomain: %s",
                self.formatted_class_name,
                self.root_domain,
            )

        return self._chatbot_custom_domain


__all__ = [
    "ChatBotHelper",
]
