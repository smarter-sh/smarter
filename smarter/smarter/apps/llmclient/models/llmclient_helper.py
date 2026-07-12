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

from .llmclient import LLMClient
from .llmclient_api_key import LLMClientAPIKey
from .llmclient_custom_domain import LLMClientCustomDomain
from .llmclient_plugin import LLMClientPlugin
from .llmclient_requests import LLMClientRequests

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING])
llmclient_helper_logger = logging.getSmarterLogger(
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
    metadata, such as the associated account, llmclient ID, and custom domain.

    Example::

        helper = LLMClientHelper(request)
        llmclient = helper.llmclient
        if helper.is_valid:
            # Proceed with llmclient logic

    :param request: The Django HttpRequest object containing the URL and user context.
    :type request: django.http.HttpRequest
    :param args: Additional positional arguments.
    :param kwargs: Additional keyword arguments, such as 'llmclient', 'llmclient_custom_domain', etc.

    :raises SmarterConfigurationError: If the helper cannot resolve a valid LLMClient instance.

    .. note::
        This class is intended for internal use within the Smarter platform and
        should not be used directly in user-facing code without proper validation.
    """

    __slots__ = (
        "_llmclient",
        "_llmclient_custom_domain",
        "_llmclient_requests",
        "_llmclient_id",
        "_name",
        "_is_llmclienthelper_ready",
    )

    def __init__(self, request: HttpRequest, *args, **kwargs):
        """
        Initializes the LLMClientHelper instance.

        :param request: The Django HttpRequest object.
        :type request: django.http.HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        """
        self._llmclient = None
        self._llmclient_custom_domain = None
        self._llmclient_requests = None
        self._llmclient_id = None
        self._name = None
        self._is_llmclienthelper_ready: bool = False

        llmclient_helper_logger.debug(
            "%s.__init__() called with url: %s args: %s, kwargs: %s",
            self.formatted_class_name,
            request.build_absolute_uri() if request else None,
            args,
            kwargs,
        )
        self._llmclient: Optional[LLMClient] = kwargs.get("llmclient")
        if isinstance(self._llmclient, LLMClient):
            llmclient_helper_logger.debug(
                "%s.__init__() received LLMClient: %s",
                self.formatted_class_name,
                str(self._llmclient),
            )
        self._llmclient_id: Optional[int] = kwargs.get("llmclient_id")
        if isinstance(self._llmclient_id, int):
            llmclient_helper_logger.debug(
                "%s.__init__() received llmclient_id: %s",
                self.formatted_class_name,
                str(self._llmclient_id),
            )
        self._name: Optional[str] = kwargs.get("name")
        if isinstance(self._name, str):
            llmclient_helper_logger.debug(
                "%s.__init__() received name: %s",
                self.formatted_class_name,
                str(self._name),
            )

        self._llmclient_custom_domain: Optional[LLMClientCustomDomain] = kwargs.get("llmclient_custom_domain")
        if isinstance(self._llmclient_custom_domain, LLMClientCustomDomain):
            llmclient_helper_logger.debug(
                "%s.__init__() received LLMClientCustomDomain: %s",
                self.formatted_class_name,
                str(self._llmclient_custom_domain),
            )
        self._llmclient_requests: Optional[LLMClientRequests] = kwargs.get("llmclient_requests")
        if isinstance(self._llmclient_requests, LLMClientRequests):
            llmclient_helper_logger.debug(
                "%s.__init__() received LLMClientRequests: %s",
                self.formatted_class_name,
                str(self._llmclient_requests),
            )

        # initializations that depend on the superclass
        super().__init__(request, *args, **kwargs)
        llmclient_helper_logger.debug("%s.__init__() completed super().__init__()", self.formatted_class_name)
        self._llmclient_id = self._llmclient_id or self.smarter_request_llmclient_id
        self._name = self._name or self.smarter_request_llmclient_name

        if self.is_llmclient:
            if not isinstance(self.llmclient, LLMClient):
                if self.user_profile and self._name:
                    try:
                        self.llmclient = LLMClient.get_cached_object(name=self._name, user_profile=self.user_profile)
                    except LLMClient.DoesNotExist:
                        llmclient_helper_logger.warning(
                            "%s.__init__() could not find LLMClient with name=%s and user_profile=%s",
                            self.formatted_class_name,
                            self._name,
                            self.user_profile,
                        )

            if not isinstance(self._llmclient, LLMClient):
                llmclient_helper_logger.warning(
                    "%s.__init__() did not find a LLMClient for url=%s, name=%s, llmclient_id=%s, user_profile=%s",
                    self.formatted_class_name,
                    self.url,
                    self.name,
                    self.llmclient_id,
                    self.user_profile,
                )

        msg = f"{self.formatted_class_name}.__init__() is {self.llmclienthelper_ready_state} - {self.llmclient if self.llmclient else 'LLMClient not initialized'} - {self.user_profile if self.user_profile else 'UserProfile not initialized'}"
        if self.ready:
            llmclient_helper_logger.debug(msg)
            llmclient_helper_logger.debug(
                "%s.__init__() initialized with url=%s, name=%s, llmclient_id=%s, user=%s, user_profile=%s, session_key=%s",
                self.formatted_class_name,
                self.url if self.url else "undefined",
                self.name,
                self.llmclient_id,
                self.user,
                self.user_profile,
                self.session_key,
            )
        else:
            llmclient_helper_logger.error(msg)

    def __str__(self):
        return str(self.llmclient) if self._llmclient else "undefined"

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
        'smarter.apps.llmclient.models.LLMClientHelper()'
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
            llmclient_helper_logger.debug("overriding account with account_number from named url: %s", self.url)
            return Account.get_cached_object(account_number=account_number)

        # from the super()
        return self._account

    @property
    def llmclient_id(self) -> Optional[int]:
        """
        Returns the :attr:`LLMClient.id` for this LLMClientHelper instance.

        This property attempts to resolve the LLMClient's unique integer ID using several strategies:

        1. If an llmclient ID was provided at initialization, it is returned immediately.
        2. If a LLMClient object is already cached, its ID is returned.
        3. If the parent :class:`SmarterRequestMixin` provides an llmclient ID (e.g., parsed from the URL), it is used.
        4. If both an llmclient name and account are available, attempts to resolve and cache the LLMClient object and its ID.

        :returns: The resolved LLMClient ID, or ``None`` if not found.
        :rtype: Optional[int]
        """
        # check for a value passed in
        if self._llmclient_id:
            return self._llmclient_id

        # check for an llmclient object
        if self._llmclient:
            self._llmclient_id = self.llmclient.id  # type: ignore[return-value]
            return self._llmclient_id

        # check SmarterRequestMixin for an llmclient_id derived from the  url
        self._llmclient_id = super().smarter_request_llmclient_id
        if self._llmclient_id:
            return self._llmclient_id

        if self.llmclient_name and self.user_profile:
            self.llmclient = LLMClient.get_cached_object(name=self.llmclient_name, user_profile=self.user_profile)
            llmclient_helper_logger.debug(
                "llmclient_id() initialized self.llmclient_id=%s from name=%s and account=%s",
                self._llmclient_id,
                self.llmclient_name,
                self.account,
            )
            return self._llmclient_id

        return self._llmclient_id

    @llmclient_id.setter
    def llmclient_id(self, llmclient_id: int):
        self._llmclient_id = llmclient_id
        llmclient = LLMClient.get_cached_object(pk=llmclient_id)
        if llmclient and llmclient.user_profile.cached_account != self.account:
            raise SmarterValueError(
                "LLMClientHelper.llmclient_id setter: LLMClient's Account does not match self.account"
            )
        self.llmclient = llmclient
        if self._llmclient:
            llmclient_helper_logger.debug(
                "@llmclient_id.setter initialized self.llmclient_id=%s from llmclient_id=%s",
                self._llmclient_id,
                llmclient_id,
            )

    @property
    def llmclient_name(self) -> Optional[str]:
        """Returns the LLMClient.name for the LLMClientHelper."""
        return self.name

    @property
    def name(self) -> Optional[str]:
        """
        Returns the name of the llmclient.

        This property attempts to resolve the llmclient's name using several strategies, in order of precedence:

        1. ``self._name``: The name assigned during initialization, if available.
        2. ``self.llmclient.name``: The name attribute of the resolved LLMClient instance, if present.
        3. ``self.subdomain``: If the URL is a named llmclient URL (i.e., ``is_llmclient_named_url`` is True), the subdomain is used as the name.
        4. Path slug: If the URL is a sandbox llmclient URL (i.e., ``is_llmclient_sandbox_url`` is True), the path slug is used as the name.

        :returns: The resolved llmclient name, or ``None`` if not found.
        :rtype: Optional[str]
        """
        if self._llmclient:
            self._name = self._llmclient.name

        return self._name

    @property
    def rfc1034_compliant_name(self) -> Optional[str]:
        """
        Returns a URL-friendly name for the llmclient.

        This is a convenience property that returns a RFC 1034 compliant name for the llmclient.

        Examples
        --------
        .. code-block:: python

            self.name  # 'Example LLMClient 1'
            self.rfc1034_compliant_name  # 'example-llmclient-1'

        :returns: The RFC 1034 compliant name for the llmclient, or ``None`` if not available.
        :rtype: Optional[str]
        """
        if self._llmclient:
            return self._llmclient.rfc1034_compliant_name
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
        if self._is_llmclienthelper_ready:
            return self._is_llmclienthelper_ready
        logger_prefix = f"{self.formatted_class_name}.is_helper_ready()"
        logger.debug(
            "%s checking readiness. Current state: url=%s, name=%s, llmclient_id=%s, user_profile=%s, llmclient=%s, llmclient_custom_domain=%s",
            logger_prefix,
            self.url,
            self.name,
            self.llmclient_id,
            self.user_profile,
            self._llmclient,
            self._llmclient_custom_domain,
        )

        if self.llmclient and isinstance(self._llmclient, LLMClient):
            llmclient_helper_logger.debug(
                "%s returning true because llmclient is initialized: %s",
                logger_prefix,
                self._llmclient,
            )
            self._is_llmclienthelper_ready = True
            return self._is_llmclienthelper_ready
        else:
            llmclient_helper_logger.debug(
                "%s llmclient is not initialized: %s",
                logger_prefix,
                self._llmclient,
            )

        if self.llmclient_custom_domain:
            llmclient_helper_logger.debug(
                "%s llmclient_custom_domain is set but LLMClientHelpler is not confirmed to be ready.",
                logger_prefix,
            )

        if not self.is_llmclient:
            llmclient_helper_logger.debug(
                "%s returning false because is_llmclient is false",
                logger_prefix,
            )
            return False
        else:
            llmclient_helper_logger.debug(
                "%s confirmed URL is an llmclient URL. url=%s",
                logger_prefix,
                self._url,
            )
        if not self.user or not self.user.is_authenticated:
            llmclient_helper_logger.warning(
                "%s returning false because called with unauthenticated request",
                logger_prefix,
            )
            return False
        else:
            llmclient_helper_logger.debug(
                "%s confirmed request user is authenticated: %s",
                logger_prefix,
                self.user.username,
            )
        if not self.account:
            llmclient_helper_logger.warning("%s returning false because called with no account", logger_prefix)
            return False
        else:
            llmclient_helper_logger.debug(
                "%s confirmed account is assigned: %s",
                logger_prefix,
                self.account,
            )
        if not isinstance(self.name, str):
            llmclient_helper_logger.warning(
                "%s returning false because did not find a name for the llmclient.", logger_prefix
            )
            return False
        else:
            llmclient_helper_logger.debug(
                "%s confirmed llmclient name is assigned: %s",
                logger_prefix,
                self.name,
            )
        if not isinstance(self._llmclient, LLMClient):
            llmclient_helper_logger.debug(
                "%s returning false because LLMClient is not initialized.",
                logger_prefix,
            )
            return False
        else:
            llmclient_helper_logger.debug(
                "%s confirmed LLMClient is initialized: %s",
                logger_prefix,
                self._llmclient,
            )
            self._is_llmclienthelper_ready = True
            return self._is_llmclienthelper_ready

    @property
    def llmclienthelper_ready_state(self) -> str:
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
            llmclient_helper_logger.debug(
                "%s.ready() returning true because LLMClientHelper is ready even though SmarterRequestMixin is not ready",
                self.formatted_class_name,
            )
            return True
        if not super().ready:
            llmclient_helper_logger.debug(
                "%s.ready() returning false because SmarterRequestMixin is not ready", self.formatted_class_name
            )
            return False

        return self.is_helper_ready

    def to_json(self) -> dict[str, Any]:
        """
        Serialize the LLMClientHelper to a dictionary.

        This method returns a dictionary representation of the LLMClientHelper instance,
        including key metadata and related objects such as the llmclient, account, and custom domain.

        :returns: A dictionary containing the serialized state of the LLMClientHelper.
        :rtype: dict[str, Any]
        """
        # pylint: disable=C0415
        from smarter.apps.llmclient.serializers import (
            LLMClientCustomDomainSerializer,
            LLMClientSerializer,
        )

        return self.sorted_dict(
            {
                "ready": self.ready,
                "name": self.name,
                "api_host": self.api_host,
                "llmclient_id": self.llmclient_id,
                "llmclient_name": self.llmclient_name,
                "llmclient_custom_domain": (
                    LLMClientCustomDomainSerializer(self.llmclient_custom_domain)
                    if self.llmclient_custom_domain
                    else None
                ),
                "environment_api_domain": smarter_settings.environment_api_domain,
                "is_custom_domain": self.is_custom_domain,
                "is_deployed": self.is_deployed,
                "is_authentication_required": self.is_authentication_required,
                "is_helper_ready": self.is_helper_ready,
                "rfc1034_compliant_name": self.rfc1034_compliant_name,
                "llmclient": LLMClientSerializer(self.llmclient).data if self.llmclient else None,
                "url": self.url,
                **super().to_json(),
            }
        )

    @cached_property
    def api_host(self) -> Optional[str]:
        """
        Returns the API host for a LLMClient API URL.

        This property extracts and returns the API host component from the llmclient URL,
        supporting named, sandbox, and custom domain URLs.

        Examples
        --------
        Named URL:
            - ``https://hr.3141-5926-5359.alpha.api.example.com/llm-client/``
              returns ``'alpha.api.example.com'``

        Sandbox URL:
            - ``http://api.localhost:9357/api/v1/llm-clients/1/prompt/``
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
        return self.llmclient.deployed if self.llmclient else False  # type: ignore[return-value]

    @cached_property
    def is_authentication_required(self) -> bool:
        """
        Determines if authentication is required to access the LLMClient.

        :returns: ``True`` if authentication is required, otherwise ``False``.
        :rtype: bool
        """
        if self.is_llmclient_sandbox_url:
            return True

        if not self.llmclient:
            return False
        llmclientapikeys = LLMClientAPIKey.get_cached_objects(llmclient=self.llmclient)
        if llmclientapikeys.filter(api_key__is_active=True).exists():
            return True
        return False

    @property
    def llmclient(self) -> Optional[LLMClient]:
        """
        Returns a lazy instance of the LLMClient.

        Examples
        --------
        - https://hr.3141-5926-5359.alpha.api.example.com/llm-client/
          returns LLMClient(name='hr', account=Account(...))

        :returns: The LLMClient instance, or ``None`` if not found.
        :rtype: Optional[LLMClient]
        """
        if self._llmclient:
            return self._llmclient

        logger.debug(
            "%s.llmclient() attempting to resolve LLMClient. Current state: url=%s, name=%s, llmclient_id=%s, user_profile=%s",
            self.formatted_class_name,
            self.url,
            self.name,
            self._llmclient_id,
            self.user_profile,
        )

        # cheapest possibility
        if self._llmclient_id:
            self._llmclient = LLMClient.get_cached_object(pk=self._llmclient_id)
            llmclient_helper_logger.debug(
                "%s.llmclient() initialized llmclient %s from llmclient_id %s",
                self.formatted_class_name,
                self._llmclient,
                self._llmclient_id,
            )
            self._is_llmclienthelper_ready = True
            return self._llmclient

        # our expected case
        if self.user_profile and self.name:
            try:
                self._llmclient = LLMClient.get_cached_object(name=self.name, user_profile=self.user_profile)
                llmclient_helper_logger.debug(
                    "%s.llmclient() initialized llmclient %s from account %s and name %s",
                    self.formatted_class_name,
                    self._llmclient,
                    self.account,
                    self.name,
                )
                self._is_llmclienthelper_ready = True
                return self._llmclient
            except LLMClient.DoesNotExist:
                llmclient_helper_logger.error(
                    "%s.llmclient() did not find llmclient for %s name: %s",
                    self.formatted_class_name,
                    self._user_profile,
                    self.name,
                )

        return self._llmclient

    @llmclient.setter
    def llmclient(self, llmclient: LLMClient):
        """Sets the LLMClient instance for this LLMClientHelper."""
        logger_prefix = f"{self.formatted_class_name}.llmclient().setter"
        if isinstance(llmclient, LLMClient):
            self._llmclient = llmclient
            self._llmclient_id = self._llmclient.id  # type: ignore[assignment]
            self._name = self._llmclient.name
            self._is_llmclienthelper_ready = True
            llmclient_helper_logger.debug(
                "%s initialized self.llmclient_id=%s and self.name=%s from llmclient",
                logger_prefix,
                self._llmclient_id,
                self._name,
            )
        elif llmclient is None:
            self._llmclient_id = None
            self._name = None
            llmclient_helper_logger.debug(
                "%s cleared self.llmclient_id and self.name because llmclient is None", logger_prefix
            )
        else:
            raise SmarterValueError(f"{logger_prefix} expected a LLMClient instance or None, got {type(llmclient)}")
        if hasattr(self, "is_helper_ready"):
            del self.is_helper_ready

    @cached_property
    def provider(self) -> Optional[Provider]:
        """
        Returns the Provider associated with the LLMClient.

        :returns: The Provider instance, or ``None`` if not found.
        :rtype: Optional[Provider]
        """
        if not self.llmclient:
            return None
        try:
            # FIX NOTE: self.llmclient.provider should be a foreign key to Provider.
            return Provider.get_cached_object(name=self.llmclient.provider, account=self.account)  # type: ignore[return-value]
        except Provider.DoesNotExist:
            return None

    @property
    def llmclient_plugins_list(self) -> list[LLMClientPlugin]:
        """
        Returns a list of LLMClientPlugin instances associated with the LLMClient.

        :returns: A list of LLMClientPlugin instances.
        :rtype: list[LLMClientPlugin]
        """
        if not self.llmclient:
            return []
        return list(LLMClientPlugin.get_cached_objects(llmclient=self.llmclient))

    @cached_property
    def llmclient_plugins_list_str(self) -> str:
        """
        Returns a comma-separated string of LLMClientPlugin names associated with the LLMClient.

        :returns: A comma-separated string of LLMClientPlugin names.
        :rtype: str
        """
        plugins = self.llmclient_plugins_list
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
        return self.llmclient_custom_domain is not None

    @property
    def llmclient_custom_domain(self) -> Optional[LLMClientCustomDomain]:
        """
        Returns a lazy instance of the LLMClientCustomDomain.

        Examples
        --------
        - ``https://hr.smarter.sh/llm-client/``
          returns ``LLMClientCustomDomain(domain_name='smarter.sh')``

        :returns: The LLMClientCustomDomain instance, or ``None`` if not found.
        :rtype: Optional[LLMClientCustomDomain]
        """
        if self._llmclient_custom_domain:
            return self._llmclient_custom_domain
        if not self.llmclient:
            return None
        if not self.llmclient.custom_domain:
            return None

        try:
            self._llmclient_custom_domain = LLMClientCustomDomain.objects.get(
                id=self.llmclient.custom_domain.id if self.llmclient.custom_domain else None  # type: ignore[union-attr]
            )
            logger.debug(
                "%s.llmclient_custom_domain() found LLMClientCustomDomain for root domain: %s %s",
                self.formatted_class_name,
                self.root_domain,
                self.user_profile,
            )
        except LLMClientCustomDomain.DoesNotExist:
            pass

        if not self._llmclient_custom_domain:
            logger.debug(
                "%s.llmclient_custom_domain() did not find LLMClientCustomDomain for rootdomain: %s",
                self.formatted_class_name,
                self.root_domain,
            )

        return self._llmclient_custom_domain


__all__ = [
    "LLMClientHelper",
]
