"""All models for the OpenAI Function Calling API app."""

from functools import cached_property
from typing import Any, Optional
from urllib.parse import ParseResult

from django.http import HttpRequest

from smarter.apps.account.models import Account
from smarter.apps.account.utils import account_number_from_url
from smarter.apps.provider.models import Provider
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.lib import logging
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .llm_client import LLMClient
from .llm_client_api_key import LLMClientAPIKey
from .llm_client_custom_domain import LLMClientCustomDomain
from .llm_client_plugin import LLMClientPlugin
from .llm_client_requests import LLMClientRequests

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING])
llm_client_helper_logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_HELPER_LOGGING]
)


class LLMClientHelper(SmarterRequestMixin):
    """
    Provides a mapping between URLs and their corresponding LLMClient models,.

    abstracting URL parsing logic for reuse across the codebase.

    This helper class is designed to centralize and standardize the logic
    required to resolve a LLMClient instance from a given URL or request context.
    It is intended for use in various locations, including within this module,
    Django middleware, and view logic.

    The class also implements caching of LLMClient objects for specific URLs,
    reducing redundant parsing and database queries for repeated requests.

    **Supported URL Patterns**

    The following are examples of valid URLs that this helper can process:

    - **Authentication Optional URLs:**
        - ``https://example-username.3141-5926-5359.alpha.api.example.com/``
        - ``https://example-username.3141-5926-5359.alpha.api.example.com/config/``

    - **Authenticated URLs:**
        - ``https://alpha.api.example-username.com/smarter/example/``
        - ``https://example-username.smarter.sh/llm-client/``
        - ``https://alpha.api.example-username.com/workbench/1/``
        - ``https://alpha.api.example-username.com/workbench/example/``

    - **Legacy (pre v0.12) URLs:**
        - ``https://alpha.api.example-username.com/llm-clients/1/``
        - ``https://alpha.api.example-username.com/llm-clients/example/``

    where for ``example-username``,  ``example`` is the LLMClient name,
    ``username`` is the Account Username, and ``3141-5926-5359`` is the
    Account Number.

    **Features**

    - Abstracts and encapsulates URL parsing and LLMClient resolution logic.
    - Provides a consistent interface for retrieving LLMClient instances from URLs.
    - Caches LLMClient objects to avoid redundant lookups.
    - Supports both authenticated and unauthenticated URL patterns.
    - Handles legacy URL formats for backward compatibility.

    **Usage**

    This class is typically instantiated with a Django ``HttpRequest`` object.
    It can then be used to access the resolved LLMClient instance and related
    metadata, such as the associated account, llm_client ID, and custom domain.

    Example::

        helper = LLMClientHelper(request)
        llm_client = helper.llm_client
        if helper.is_valid:
            # Proceed with llm_client logic

    :param request: The Django HttpRequest object containing the URL and user context.
    :type request: django.http.HttpRequest
    :param args: Additional positional arguments.
    :param kwargs: Additional keyword arguments, such as 'llm_client', 'llm_client_custom_domain', etc.

    :raises SmarterConfigurationError: If the helper cannot resolve a valid LLMClient instance.

    .. note::
        This class is intended for internal use within the Smarter platform and
        should not be used directly in user-facing code without proper validation.
    """

    __slots__ = (
        "_llm_client",
        "_llm_client_custom_domain",
        "_llm_client_requests",
        "_llm_client_id",
        "_name",
        "_is_llm_clienthelper_ready",
    )

    def __init__(self, request: HttpRequest, *args, **kwargs):
        """
        Initializes the LLMClientHelper instance.

        :param request: The Django HttpRequest object.
        :type request: django.http.HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        """
        self._llm_client = None
        self._llm_client_custom_domain = None
        self._llm_client_requests = None
        self._llm_client_id = None
        self._name = None
        self._is_llm_clienthelper_ready: bool = False

        llm_client_helper_logger.debug(
            "%s.__init__() called with url: %s args: %s, kwargs: %s",
            self.formatted_class_name,
            request.build_absolute_uri() if request else None,
            args,
            kwargs,
        )
        self._llm_client: Optional[LLMClient] = kwargs.get("llm_client")
        if isinstance(self._llm_client, LLMClient):
            llm_client_helper_logger.debug(
                "%s.__init__() received LLMClient: %s",
                self.formatted_class_name,
                str(self._llm_client),
            )
        self._llm_client_id: Optional[int] = kwargs.get("llm_client_id")
        if isinstance(self._llm_client_id, int):
            llm_client_helper_logger.debug(
                "%s.__init__() received llm_client_id: %s",
                self.formatted_class_name,
                str(self._llm_client_id),
            )
        self._name: Optional[str] = kwargs.get("name")
        if isinstance(self._name, str):
            llm_client_helper_logger.debug(
                "%s.__init__() received name: %s",
                self.formatted_class_name,
                str(self._name),
            )

        self._llm_client_custom_domain: Optional[LLMClientCustomDomain] = kwargs.get("llm_client_custom_domain")
        if isinstance(self._llm_client_custom_domain, LLMClientCustomDomain):
            llm_client_helper_logger.debug(
                "%s.__init__() received LLMClientCustomDomain: %s",
                self.formatted_class_name,
                str(self._llm_client_custom_domain),
            )
        self._llm_client_requests: Optional[LLMClientRequests] = kwargs.get("llm_client_requests")
        if isinstance(self._llm_client_requests, LLMClientRequests):
            llm_client_helper_logger.debug(
                "%s.__init__() received LLMClientRequests: %s",
                self.formatted_class_name,
                str(self._llm_client_requests),
            )

        # initializations that depend on the superclass
        super().__init__(request, *args, **kwargs)
        llm_client_helper_logger.debug("%s.__init__() completed super().__init__()", self.formatted_class_name)
        self._llm_client_id = self._llm_client_id or self.smarter_request_llm_client_id
        self._name = self._name or self.smarter_request_llm_client_name

        if self.is_llm_client:
            if not isinstance(self.llm_client, LLMClient):
                if self.user_profile and self._name:
                    try:
                        self.llm_client = LLMClient.get_cached_object(name=self._name, user_profile=self.user_profile)
                    except LLMClient.DoesNotExist:
                        llm_client_helper_logger.warning(
                            "%s.__init__() could not find LLMClient with name=%s and user_profile=%s",
                            self.formatted_class_name,
                            self._name,
                            self.user_profile,
                        )

            if not isinstance(self._llm_client, LLMClient):
                llm_client_helper_logger.warning(
                    "%s.__init__() did not find a LLMClient for url=%s, name=%s, llm_client_id=%s, user_profile=%s",
                    self.formatted_class_name,
                    self.url,
                    self.name,
                    self.llm_client_id,
                    self.user_profile,
                )

        msg = f"{self.formatted_class_name}.__init__() is {self.llm_clienthelper_ready_state} - {self.llm_client if self.llm_client else 'LLMClient not initialized'} - {self.user_profile if self.user_profile else 'UserProfile not initialized'}"
        if self.ready:
            llm_client_helper_logger.debug(msg)
            llm_client_helper_logger.debug(
                "%s.__init__() initialized with url=%s, name=%s, llm_client_id=%s, user=%s, user_profile=%s, session_key=%s",
                self.formatted_class_name,
                self.url if self.url else "undefined",
                self.name,
                self.llm_client_id,
                self.user,
                self.user_profile,
                self.session_key,
            )
        else:
            llm_client_helper_logger.error(msg)

    def __str__(self):
        return str(self.llm_client) if self._llm_client else "undefined"

    @cached_property
    def formatted_class_name(self) -> str:
        """
        Get the formatted class name for this instance of LLMClientHelper.

        :returns: The formatted class name as a string, including the parent class name.
        :rtype: str

        This property returns a string representation of the class name,
        formatted to include the parent class's formatted name and the
        ``LLMClientHelper`` class. This is useful for logging and debugging
        purposes, as it provides a clear and consistent identifier for
        instances of this helper class.

        Example
        -------
        >>> helper = LLMClientHelper(request)
        >>> helper.formatted_class_name
        'smarter.apps.llm_client.models.LLMClientHelper()'
        """
        class_name = f"{__name__}.{LLMClientHelper.__name__}()[{id(self)}]"
        return self.formatted_text(class_name)

    @cached_property
    def account(self) -> Optional[Account]:
        """
        Return the associated :class:`Account` for this LLMClientHelper instance,.

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
            llm_client_helper_logger.debug("overriding account with account_number from named url: %s", self.url)
            return Account.get_cached_object(account_number=account_number)

        # from the super()
        return self._account

    @property
    def llm_client_id(self) -> Optional[int]:
        """
        Returns the :attr:`LLMClient.id` for this LLMClientHelper instance.

        This property attempts to resolve the LLMClient's unique integer ID using several strategies:

        1. If an llm_client ID was provided at initialization, it is returned immediately.
        2. If a LLMClient object is already cached, its ID is returned.
        3. If the parent :class:`SmarterRequestMixin` provides an llm_client ID (e.g., parsed from the URL), it is used.
        4. If both an llm_client name and account are available, attempts to resolve and cache the LLMClient object and its ID.

        :returns: The resolved LLMClient ID, or ``None`` if not found.
        :rtype: Optional[int]
        """
        # check for a value passed in
        if self._llm_client_id:
            return self._llm_client_id

        # check for an llm_client object
        if self._llm_client:
            self._llm_client_id = self.llm_client.id  # type: ignore[return-value]
            return self._llm_client_id

        # check SmarterRequestMixin for an llm_client_id derived from the  url
        self._llm_client_id = super().smarter_request_llm_client_id
        if self._llm_client_id:
            return self._llm_client_id

        if self.llm_client_name and self.user_profile:
            self.llm_client = LLMClient.get_cached_object(name=self.llm_client_name, user_profile=self.user_profile)
            llm_client_helper_logger.debug(
                "llm_client_id() initialized self.llm_client_id=%s from name=%s and account=%s",
                self._llm_client_id,
                self.llm_client_name,
                self.account,
            )
            return self._llm_client_id

        return self._llm_client_id

    @llm_client_id.setter
    def llm_client_id(self, llm_client_id: int):
        self._llm_client_id = llm_client_id
        llm_client = LLMClient.get_cached_object(pk=llm_client_id)
        if llm_client and llm_client.user_profile.cached_account != self.account:
            raise SmarterValueError(
                "LLMClientHelper.llm_client_id setter: LLMClient's Account does not match self.account"
            )
        self.llm_client = llm_client
        if self._llm_client:
            llm_client_helper_logger.debug(
                "@llm_client_id.setter initialized self.llm_client_id=%s from llm_client_id=%s",
                self._llm_client_id,
                llm_client_id,
            )

    @property
    def llm_client_name(self) -> Optional[str]:
        """Returns the LLMClient.name for the LLMClientHelper."""
        return self.name

    @property
    def name(self) -> Optional[str]:
        """
        Returns the name of the llm_client.

        This property attempts to resolve the llm_client's name using several strategies, in order of precedence:

        1. ``self._name``: The name assigned during initialization, if available.
        2. ``self.llm_client.name``: The name attribute of the resolved LLMClient instance, if present.
        3. ``self.subdomain``: If the URL is a named llm_client URL (i.e., ``is_llm_client_named_url`` is True), the subdomain is used as the name.
        4. Path slug: If the URL is a sandbox llm_client URL (i.e., ``is_llm_client_sandbox_url`` is True), the path slug is used as the name.

        :returns: The resolved llm_client name, or ``None`` if not found.
        :rtype: Optional[str]
        """
        if self._llm_client:
            self._name = self._llm_client.name

        return self._name

    @property
    def rfc1034_compliant_name(self) -> Optional[str]:
        """
        Returns a URL-friendly name for the llm_client.

        This is a convenience property that returns a RFC 1034 compliant name for the llm_client.

        Examples
        --------
        .. code-block:: python

            self.name  # 'Example LLMClient 1'
            self.rfc1034_compliant_name  # 'example-llm_client-1'

        :returns: The RFC 1034 compliant name for the llm_client, or ``None`` if not available.
        :rtype: Optional[str]
        """
        if self._llm_client:
            return self._llm_client.rfc1034_compliant_name
        return None

    @cached_property
    def is_helper_ready(self) -> bool:
        """
        Returns ``True`` if the LLMClientHelper is ready to be used.

        This is a convenience property that checks if the LLMClientHelper
        is initialized and has a valid :class:`LLMClient` instance.

        :returns: ``True`` if the helper is initialized and has a valid LLMClient, otherwise ``False``.
        :rtype: bool
        """
        if self._is_llm_clienthelper_ready:
            return self._is_llm_clienthelper_ready
        logger_prefix = f"{self.formatted_class_name}.is_helper_ready()"
        logger.debug(
            "%s checking readiness. Current state: url=%s, name=%s, llm_client_id=%s, user_profile=%s, llm_client=%s, llm_client_custom_domain=%s",
            logger_prefix,
            self.url,
            self.name,
            self.llm_client_id,
            self.user_profile,
            self._llm_client,
            self._llm_client_custom_domain,
        )

        if self.llm_client and isinstance(self._llm_client, LLMClient):
            llm_client_helper_logger.debug(
                "%s returning true because llm_client is initialized: %s",
                logger_prefix,
                self._llm_client,
            )
            self._is_llm_clienthelper_ready = True
            return self._is_llm_clienthelper_ready
        else:
            llm_client_helper_logger.debug(
                "%s llm_client is not initialized: %s",
                logger_prefix,
                self._llm_client,
            )

        if self.llm_client_custom_domain:
            llm_client_helper_logger.debug(
                "%s llm_client_custom_domain is set but LLMClientHelpler is not confirmed to be ready.",
                logger_prefix,
            )

        if not self.is_llm_client:
            llm_client_helper_logger.debug(
                "%s returning false because is_llm_client is false",
                logger_prefix,
            )
            return False
        else:
            llm_client_helper_logger.debug(
                "%s confirmed URL is an llm_client URL. url=%s",
                logger_prefix,
                self._url,
            )
        if not self.user or not self.user.is_authenticated:
            llm_client_helper_logger.warning(
                "%s returning false because called with unauthenticated request",
                logger_prefix,
            )
            return False
        else:
            llm_client_helper_logger.debug(
                "%s confirmed request user is authenticated: %s",
                logger_prefix,
                self.user.username,
            )
        if not self.account:
            llm_client_helper_logger.warning("%s returning false because called with no account", logger_prefix)
            return False
        else:
            llm_client_helper_logger.debug(
                "%s confirmed account is assigned: %s",
                logger_prefix,
                self.account,
            )
        if not isinstance(self.name, str):
            llm_client_helper_logger.warning(
                "%s returning false because did not find a name for the llm_client.", logger_prefix
            )
            return False
        else:
            llm_client_helper_logger.debug(
                "%s confirmed llm_client name is assigned: %s",
                logger_prefix,
                self.name,
            )
        if not isinstance(self._llm_client, LLMClient):
            llm_client_helper_logger.debug(
                "%s returning false because LLMClient is not initialized.",
                logger_prefix,
            )
            return False
        else:
            llm_client_helper_logger.debug(
                "%s confirmed LLMClient is initialized: %s",
                logger_prefix,
                self._llm_client,
            )
            self._is_llm_clienthelper_ready = True
            return self._is_llm_clienthelper_ready

    @property
    def llm_clienthelper_ready_state(self) -> str:
        """
        Returns a formatted string indicating whether the LLMClientHelper is ready.

        :return: A string indicating whether the LLMClientHelper is ready or not.
        """
        return (
            logging.formatted_text_green("Ready") if self.is_helper_ready else logging.formatted_text_red("Not Ready")
        )

    @property
    def ready(self) -> bool:
        """
        Returns ``True`` if the LLMClientHelper and its LLMClient are ready to be used.

        This property checks both the readiness of the LLMClientHelper itself and the readiness
        of the underlying LLMClient instance.

        :returns: ``True`` if both the helper and LLMClient are ready, otherwise ``False``.
        :rtype: bool
        """
        # there is a scenario where the SmarterRequestMixin is not ready but the LLMClientHelper is.
        if self.is_helper_ready and self.user_profile and not super().ready:
            llm_client_helper_logger.debug(
                "%s.ready() returning true because LLMClientHelper is ready even though SmarterRequestMixin is not ready",
                self.formatted_class_name,
            )
            return True
        if not super().ready:
            llm_client_helper_logger.debug(
                "%s.ready() returning false because SmarterRequestMixin is not ready", self.formatted_class_name
            )
            return False

        return self.is_helper_ready

    def to_json(self) -> dict[str, Any]:
        """
        Serialize the LLMClientHelper to a dictionary.

        This method returns a dictionary representation of the LLMClientHelper instance,
        including key metadata and related objects such as the llm_client, account, and custom domain.

        :returns: A dictionary containing the serialized state of the LLMClientHelper.
        :rtype: dict[str, Any]
        """
        # pylint: disable=C0415
        from smarter.apps.llm_client.serializers import (
            LLMClientCustomDomainSerializer,
            LLMClientSerializer,
        )

        return self.sorted_dict(
            {
                "ready": self.ready,
                "name": self.name,
                "api_host": self.api_host,
                "llm_client_id": self.llm_client_id,
                "llm_client_name": self.llm_client_name,
                "llm_client_custom_domain": (
                    LLMClientCustomDomainSerializer(self.llm_client_custom_domain)
                    if self.llm_client_custom_domain
                    else None
                ),
                "environment_api_domain": smarter_settings.environment_api_domain,
                "is_custom_domain": self.is_custom_domain,
                "is_deployed": self.is_deployed,
                "is_authentication_required": self.is_authentication_required,
                "is_helper_ready": self.is_helper_ready,
                "rfc1034_compliant_name": self.rfc1034_compliant_name,
                "llm_client": LLMClientSerializer(self.llm_client).data if self.llm_client else None,
                "url": self.url,
                **super().to_json(),
            }
        )

    @cached_property
    def api_host(self) -> Optional[str]:
        """
        Returns the API host for a LLMClient API URL.

        This property extracts and returns the API host component from the llm_client URL,
        supporting named, sandbox, and custom domain URLs.

        Examples
        --------
        Named URL:
            - ``https://hr.3141-5926-5359.alpha.api.example.com/llm-client/``
              returns ``'alpha.api.example.com'``

        Sandbox URL:
            - ``http://api.localhost:9357/api/v1/llm-clients/1/chat/``
              returns ``'api.localhost:9357'``

        Custom domain URL:
            - ``https://hr.smarter.sh/llm-client/``
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
        return self.llm_client.deployed if self.llm_client else False  # type: ignore[return-value]

    @cached_property
    def is_authentication_required(self) -> bool:
        """
        Determines if authentication is required to access the LLMClient.

        :returns: ``True`` if authentication is required, otherwise ``False``.
        :rtype: bool
        """
        if self.is_llm_client_sandbox_url:
            return True

        if not self.llm_client:
            return False
        llm_clientapikeys = LLMClientAPIKey.get_cached_objects(llm_client=self.llm_client)
        if llm_clientapikeys.filter(api_key__is_active=True).exists():
            return True
        return False

    @property
    def llm_client(self) -> Optional[LLMClient]:
        """
        Returns a lazy instance of the LLMClient.

        Examples
        --------
        - https://hr.3141-5926-5359.alpha.api.example.com/llm-client/
          returns LLMClient(name='hr', account=Account(...))

        :returns: The LLMClient instance, or ``None`` if not found.
        :rtype: Optional[LLMClient]
        """
        if self._llm_client:
            return self._llm_client

        logger.debug(
            "%s.llm_client() attempting to resolve LLMClient. Current state: url=%s, name=%s, llm_client_id=%s, user_profile=%s",
            self.formatted_class_name,
            self.url,
            self.name,
            self._llm_client_id,
            self.user_profile,
        )

        # cheapest possibility
        if self._llm_client_id:
            self._llm_client = LLMClient.get_cached_object(pk=self._llm_client_id)
            llm_client_helper_logger.debug(
                "%s.llm_client() initialized llm_client %s from llm_client_id %s",
                self.formatted_class_name,
                self._llm_client,
                self._llm_client_id,
            )
            self._is_llm_clienthelper_ready = True
            return self._llm_client

        # our expected case
        if self.user_profile and self.name:
            try:
                self._llm_client = LLMClient.get_cached_object(name=self.name, user_profile=self.user_profile)
                llm_client_helper_logger.debug(
                    "%s.llm_client() initialized llm_client %s from account %s and name %s",
                    self.formatted_class_name,
                    self._llm_client,
                    self.account,
                    self.name,
                )
                self._is_llm_clienthelper_ready = True
                return self._llm_client
            except LLMClient.DoesNotExist:
                llm_client_helper_logger.error(
                    "%s.llm_client() did not find llm_client for %s name: %s",
                    self.formatted_class_name,
                    self._user_profile,
                    self.name,
                )

        return self._llm_client

    @llm_client.setter
    def llm_client(self, llm_client: LLMClient):
        """Sets the LLMClient instance for this LLMClientHelper."""
        logger_prefix = f"{self.formatted_class_name}.llm_client().setter"
        if isinstance(llm_client, LLMClient):
            self._llm_client = llm_client
            self._llm_client_id = self._llm_client.id  # type: ignore[assignment]
            self._name = self._llm_client.name
            self._is_llm_clienthelper_ready = True
            llm_client_helper_logger.debug(
                "%s initialized self.llm_client_id=%s and self.name=%s from llm_client",
                logger_prefix,
                self._llm_client_id,
                self._name,
            )
        elif llm_client is None:
            self._llm_client_id = None
            self._name = None
            llm_client_helper_logger.debug(
                "%s cleared self.llm_client_id and self.name because llm_client is None", logger_prefix
            )
        else:
            raise SmarterValueError(f"{logger_prefix} expected a LLMClient instance or None, got {type(llm_client)}")
        if hasattr(self, "is_helper_ready"):
            del self.is_helper_ready

    @cached_property
    def provider(self) -> Optional[Provider]:
        """
        Returns the Provider associated with the LLMClient.

        :returns: The Provider instance, or ``None`` if not found.
        :rtype: Optional[Provider]
        """
        if not self.llm_client:
            return None
        try:
            # FIX NOTE: self.llm_client.provider should be a foreign key to Provider.
            return Provider.get_cached_object(name=self.llm_client.provider, account=self.account)  # type: ignore[return-value]
        except Provider.DoesNotExist:
            return None

    @property
    def llm_client_plugins_list(self) -> list[LLMClientPlugin]:
        """
        Returns a list of LLMClientPlugin instances associated with the LLMClient.

        :returns: A list of LLMClientPlugin instances.
        :rtype: list[LLMClientPlugin]
        """
        if not self.llm_client:
            return []
        return list(LLMClientPlugin.get_cached_objects(llm_client=self.llm_client))

    @cached_property
    def llm_client_plugins_list_str(self) -> str:
        """
        Returns a comma-separated string of LLMClientPlugin names associated with the LLMClient.

        :returns: A comma-separated string of LLMClientPlugin names.
        :rtype: str
        """
        plugins = self.llm_client_plugins_list
        return ", ".join(
            str(plugin.plugin_meta.name) + " (" + str(plugin.plugin_meta.user_profile) + ")" for plugin in plugins
        )

    @property
    def is_custom_domain(self) -> bool:
        """
        Returns ``True`` if the LLMClient is using a custom domain.

        :returns: ``True`` if a custom domain is configured, otherwise ``False``.
        :rtype: bool
        """
        return self.llm_client_custom_domain is not None

    @property
    def llm_client_custom_domain(self) -> Optional[LLMClientCustomDomain]:
        """
        Returns a lazy instance of the LLMClientCustomDomain.

        Examples
        --------
        - ``https://hr.smarter.sh/llm-client/``
          returns ``LLMClientCustomDomain(domain_name='smarter.sh')``

        :returns: The LLMClientCustomDomain instance, or ``None`` if not found.
        :rtype: Optional[LLMClientCustomDomain]
        """
        if self._llm_client_custom_domain:
            return self._llm_client_custom_domain
        if not self.llm_client:
            return None
        if not self.llm_client.custom_domain:
            return None

        try:
            self._llm_client_custom_domain = LLMClientCustomDomain.objects.get(
                id=self.llm_client.custom_domain.id if self.llm_client.custom_domain else None  # type: ignore[union-attr]
            )
            logger.debug(
                "%s.llm_client_custom_domain() found LLMClientCustomDomain for root domain: %s %s",
                self.formatted_class_name,
                self.root_domain,
                self.user_profile,
            )
        except LLMClientCustomDomain.DoesNotExist:
            pass

        if not self._llm_client_custom_domain:
            logger.debug(
                "%s.llm_client_custom_domain() did not find LLMClientCustomDomain for rootdomain: %s",
                self.formatted_class_name,
                self.root_domain,
            )

        return self._llm_client_custom_domain


__all__ = [
    "LLMClientHelper",
]
