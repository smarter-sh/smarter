"""Smarter API command-line interface Base class API view"""

import logging
import re
import traceback
from http import HTTPStatus
from typing import Any, Optional, Type

from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView

from smarter.apps.api.signals import (
    api_request_completed,
    api_request_failed,
    api_request_initiated,
)
from smarter.apps.api.v1.cli.brokers import Brokers
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.api.v1.manifests.version import SMARTER_API_VERSION
from smarter.apps.chatbot.exceptions import SmarterChatBotException
from smarter.apps.docs.views.base import DocsError
from smarter.apps.plugin.plugin.base import SmarterPluginError
from smarter.apps.prompt.views import SmarterChatappViewError
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_IS_INTERNAL_API_REQUEST
from smarter.common.exceptions import (
    SmarterBusinessRuleViolation,
    SmarterConfigurationError,
    SmarterException,
    SmarterIlligalInvocationError,
    SmarterInvalidApiKeyError,
    SmarterValueError,
)
from smarter.common.helpers.aws.exceptions import SmarterAWSError
from smarter.common.helpers.k8s_helpers import KubernetesHelperException
from smarter.common.utils import (
    is_authenticated_request,
    mask_string,
    smarter_build_absolute_uri,
)
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.django.token_generators import SmarterTokenError
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.token_authentication import SmarterTokenAuthentication
from smarter.lib.drf.view_helpers import SmarterAuthenticatedPermissionClass
from smarter.lib.journal.enum import (
    SmarterJournalCliCommands,
    SmarterJournalEnumException,
)
from smarter.lib.journal.http import SmarterJournaledJsonErrorResponse
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.broker import (
    AbstractBroker,
    SAMBrokerError,
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
    SAMBrokerReadOnlyError,
)
from smarter.lib.manifest.exceptions import SAMBadRequestError
from smarter.lib.manifest.loader import SAMLoader

from .swagger import BUG_REPORT


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class APIV1CLIViewError(SmarterException):
    """Base class for all APIV1CLIView errors."""

    @property
    def get_formatted_err_message(self):
        return "Smarter api v1 command-line interface error"


class SmarterAPIV1CLIViewErrorNotAuthenticated(APIV1CLIViewError):
    """Error class for not authenticated errors."""

    @property
    def get_formatted_err_message(self):
        return "Smarter api v1 command-line interface error: not authenticated"


class CliBaseApiView(APIView, SmarterRequestMixin):
    """
    Base class for all Smarter API v1 command-line interface (CLI) views.
    This class provides common functionality for all `/api/v1/cli` endpoints, including:

    - Authentication using either Knox TokenAuthentication or Django SessionAuthentication.
    - Initialization of the :class:`SAMLoader` and :class:`AbstractBroker` instances.
    - Resolution of the manifest kind and broker for the YAML manifest document.
    - Setting the user profile for the request.

    The base class is responsible for as much request "housekeeping" as possible, so that
    child views can focus on business logic. The following attributes are set up and managed:


    Notes
    -----
    - The base class is designed to minimize boilerplate in child views.
    - Manifest parsing and broker instantiation are implemented lazily.
    - Authentication is enforced by default, but can be bypassed for internal API requests.

    Examples
    --------
    Example URL with a manifest name:
        ``/api/v1/cli/describe/chatbot/<str:name>/``

    Example command extraction:
        If the URL path is ``/api/v1/cli/apply/``, then the command will be
        :attr:`SmarterJournalCliCommands.APPLY`.
    """

    permission_classes = (SmarterAuthenticatedPermissionClass,)
    authentication_classes = (SmarterTokenAuthentication,)

    _BrokerClass: Optional[Type[AbstractBroker]] = None
    _broker: Optional[AbstractBroker] = None
    _loader: Optional[SAMLoader] = None
    _manifest_data: Optional[dict] = None
    _manifest_kind: Optional[str] = None
    _manifest_name: Optional[str] = None
    _manifest_load_failed: bool = False
    _params: Optional[dict[str, Any]] = None
    _prompt: Optional[str] = None

    def __init__(self, *args, **kwargs):
        request = None
        super().__init__(*args, **kwargs)

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the class name in a formatted string
        along with the name of this mixin.

        :return: Formatted class name string
        :rtype: str
        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.CliBaseApiView()"

    @property
    def loader(self) -> Optional[SAMLoader]:
        """
        Get the SAMLoader instance. a SAMLoader instance is used to load
        raw manifest text into a Pydantic model. It performs cursory validations
        such as validating the file format, and identifying required dict key values
        such as the api version, the manifest kind and its name.

        The loader is instantiated lazily, so it will only be created
        when it is first accessed.

        :return: SAMLoader instance or None
        :rtype: Optional[SAMLoader]
        """
        if not self._loader and self.manifest_data and not self._manifest_load_failed:
            try:
                self._loader = SAMLoader(
                    api_version=SMARTER_API_VERSION,
                    kind=self.manifest_kind,
                    manifest=json.dumps(self.manifest_data),
                )
                if not self._loader or not self._loader.ready:
                    raise APIV1CLIViewError("SAMLoader is not ready.")
            except APIV1CLIViewError:
                # not all endpoints require a manifest, so we
                # should fail quietly if the manifest is not provided.
                self._manifest_load_failed = True

        return self._loader

    @property
    def BrokerClass(self) -> Type[AbstractBroker]:
        """
        Get the broker class for the manifest kind. This is used to
        instantiate a broker for the manifest kind.

        :return: Broker class for the manifest kind
        :rtype: Type[AbstractBroker]
        """
        if not self._BrokerClass:
            if self.manifest_kind:
                self._BrokerClass = Brokers.get_broker(self.manifest_kind)
            if not self._BrokerClass:
                raise APIV1CLIViewError(
                    f"Could not find broker for {self.manifest_kind or "<-- Missing -->"} manifest."
                )
        return self._BrokerClass

    @property
    def broker(self) -> AbstractBroker:
        """
        Use a loader to try to instantiate a broker. A broker is a class that
        implements the broker service pattern. It provides a service interface
        that 'brokers' the http request for the underlying object that provides
        the object-specific service (create, update, get, delete, etc).

        :return: Broker instance for the manifest kind
        :rtype: AbstractBroker
        """
        if not self._broker:
            BrokerClass = self.BrokerClass
            self._broker = BrokerClass(
                request=self.smarter_request,
                api_version=SMARTER_API_VERSION,
                name=self.manifest_name,
                kind=self.manifest_kind,
                account=self.user_profile.account if self.user_profile else None,
                loader=self.loader,
                manifest=self.loader.yaml_data if self.loader else None,
            )
            if not self._broker:
                raise APIV1CLIViewError("Could not load manifest.")

        return self._broker

    @property
    def manifest_data(self) -> Optional[dict]:
        """
        The raw manifest data from the request body. The manifest data is a json object
        which needs to be rendered into a Pydantic model. The Pydantic model is then
        used to instantiate a broker for the manifest kind.

        :return: Raw manifest data as a json object
        :rtype: Optional[dict]
        """
        if self._manifest_data:
            # belt & suspenders: ensure that the manifest data is a json object.
            if isinstance(self._manifest_data, str):
                self._manifest_data = json.loads(self._manifest_data)
        return self._manifest_data

    @property
    def manifest_name(self) -> Optional[str]:
        """
        The name of the manifest. The manifest name is used to identify the resource
        within a Kind. For example, the manifest name for a ChatBot resource is the
        name of the chatbot. The manifest name is used to identify the resource
        within a Kind. The name can be passed from inside the raw manifest data, or
        it can be passed as part of a url path.

        Example url path with a name: /api/v1/cli/describe/chatbot/<str:name>/

        :return: The name of the manifest
        :rtype: Optional[str]
        """
        if not self._manifest_name and self.manifest_data:
            self._manifest_name = self.manifest_data.get("metadata", {}).get("name", None)
        if not self._manifest_kind and self.loader:
            self._manifest_kind = self.loader.manifest_metadata.get("name") if self.loader else None
        return self._manifest_name

    @property
    def manifest_kind(self) -> str:
        """
        The kind of the manifest. The manifest kind is used to identify the type
        of resource that the manifest is describing. The kind is used to identify
        the broker that will be used to broker the http request for the resource.

        :return: The kind of the manifest
        :rtype: str
        """
        if not self._manifest_kind and self.manifest_data:
            self._manifest_kind = str(self.manifest_data.get("kind", None))
        if not self._manifest_kind and self.loader:
            self._manifest_kind = str(self.loader.manifest_kind) if self.loader else None

        # if we still don't have a manifest kind, then we should
        # analyze the url path to determine the manifest kind.
        # urls:
        # - http://testserver/api/v1/cli/logs/Chatbot/?name=TestChatBot
        # - http://testserver/api/v1/cli/chat/config/TestChatBot/
        if not self._manifest_kind:
            self._manifest_kind = SAMKinds.from_url(self.url)
            if self._manifest_kind:
                logger.warning("setting manifest kind to %s from analysis of url %s", self._manifest_kind, self.url)

        # may or may not have a manifest kind at this point.
        # anti examples:
        # - http://testserver/api/v1/cli/whoami/
        # - http://testserver/api/v1/cli/apply/
        return self._manifest_kind

    @property
    def command(self) -> SmarterJournalCliCommands:
        """
        Translate the request route into a SmarterJournalCliCommands enum
        instance. For example, if the route is '/api/v1/cli/apply/', then
        the corresponding command will be SmarterJournalCliCommands.APPLY.

        url:
         - http://testserver/api/v1/cli/logs/Chatbot/?name=TestChatBot
         - http://testserver/api/v1/cli/apply

        :return: SmarterJournalCliCommands enum instance
        :rtype: SmarterJournalCliCommands
        """
        match = re.search(r"/cli/([^/]+)/", self.url or "")
        if match:
            _command = match.group(1)
            return SmarterJournalCliCommands(_command)
        raise APIV1CLIViewError(f"Could not determine command from url: {self.url}")

    def setup(self, request: Request, *args, **kwargs):
        """
        Setup the view. This is called by Django before dispatch() and is used to
        set up the view for the request.

        :param request: The HTTP request object
        :type request: Request
        """
        super().setup(request, *args, **kwargs)
        SmarterRequestMixin.__init__(self, request=request, *args, **kwargs)

        # note: setup() is the earliest point in the request lifecycle where we can
        # send signals.
        api_request_initiated.send(sender=self.__class__, instance=self, request=request)
        logger.info(
            "CliBaseApiView().setup() - finished for request: %s, user: %s, self.user: %s is_authenticated: %s",
            smarter_build_absolute_uri(request),
            request.user.username if request.user else "Anonymous",  # type: ignore[assignment]
            self.user_profile,
            is_authenticated_request(request),
        )

    def initial(self, request: Request, *args, **kwargs):
        """
        Perform view initialization after setup and before dispatch.

        This method is called by Django REST Framework (DRF) after the `setup()` method
        but before the `dispatch()` method. It is the earliest point in the DRF view
        lifecycle where the request object is fully available and can be used to
        complete any additional initialization required by the view.

        In DRF, the `initial()` method is responsible for performing tasks such as:
        - Completing any remaining setup that depends on the request object.
        - Enforcing authentication and permission checks.
        - Raising appropriate exceptions if the request is not valid or not authenticated.

        In this implementation, `initial()` ensures that the `SmarterRequestMixin` and
        any related mixins are fully initialized with the request object. It also
        performs authentication checks, sets up user and account context, and prepares
        manifest data or prompt text for downstream processing. If authentication fails,
        it raises a custom error with detailed logging.

        Parameters
        ----------
        request : Request
            The HTTP request object provided by DRF. This object contains all
            request data, headers, user information, and other context needed
            for processing the API call.

        *args
            Additional positional arguments passed to the view.

        **kwargs
            Additional keyword arguments passed to the view, often including
            URL parameters extracted by the router.

        Raises
        ------
        SmarterAPIV1CLIViewErrorNotAuthenticated
            If the request is not authenticated and is not an internal API request,
            this exception is raised to indicate authentication failure.

        SmarterConfigurationError
            If the request object is not properly set up in the view, this error
            is raised to indicate a misconfiguration.

        Notes
        -----
        - This method is a critical part of the DRF request lifecycle, ensuring that
          all necessary context and validation is in place before the main handler
          methods (`get`, `post`, etc.) are called.
        - Manifest parsing and broker instantiation are deferred (lazy) and only
          performed when needed by child views.
        - The method also logs key events and warnings for observability.

        See Also
        --------
        https://www.django-rest-framework.org/api-guide/views/#view-initialization
            DRF documentation on the view initialization process.
        """
        url = smarter_build_absolute_uri(request)
        logger.info("%s.initial() - called for request: %s", self.formatted_class_name, url)
        if not self.is_requestmixin_ready:
            logger.info(
                "%s.initial() - completing initialization of SmarterRequestMixin with request: %s",
                self.formatted_class_name,
                url,
            )
            self.smarter_request = request

        # Check if the request is authenticated. If not, raise an
        # authentication error. see SmarterTokenAuthentication for details
        # on how the token is validated.
        # The token is passed in the Authorization header as a Bearer token
        # of the form: 'Authorization: Token YOUR-64-CHARACTER-SMARTER-API-KEY'
        try:
            super().initial(request, *args, **kwargs)
            self.user = request.user if request and getattr(request, "user", None) and getattr(request.user, "is_authenticated", False) else None  # type: ignore[assignment]

            logger.info(
                "%s.initial() - authenticated request: %s, user: %s, self.user: %s is_authenticated: %s, auth_header: %s",
                self.formatted_class_name,
                url,
                request.user.username if request.user else "Anonymous",  # type: ignore[assignment]
                self.user_profile,
                is_authenticated_request(request),
                mask_string(str(request.META.get("HTTP_AUTHORIZATION"))),
            )
        except NotAuthenticated as e:
            internal_api_request = getattr(request, SMARTER_IS_INTERNAL_API_REQUEST, False)
            if internal_api_request:
                logger.info(
                    "%s.initial() - internal api request. Skipping authentication: %s",
                    self.formatted_class_name,
                    url,
                )
            else:
                # regardless of the authentication error, we still need to
                # initialize the SmarterRequestMixin so that we can
                # access the request object, headers, url, etc.
                auth_header = request.headers.get("Authorization")
                if auth_header:
                    logger.error(
                        "%s.initial() - Authorization header contains an invalid, inactive or malformed token: %s",
                        self.formatted_class_name,
                        e,
                    )
                else:
                    logger.error(
                        "%s.initial() - Authorization header is missing from the http request. Add an http header of the form, 'Authorization: Token YOUR-64-CHARACTER-SMARTER-API-KEY' or contact support@smarter.sh %s",
                        self.formatted_class_name,
                        e,
                    )
                raise SmarterAPIV1CLIViewErrorNotAuthenticated(
                    "Smarter api v1 command-line interface error: authentication failed"
                ) from e

        # if we got here, then the request is authenticated, and we need to
        # restore the user object for the request, which DRF will have set
        # to an AnonymousUser at the start of its own authentication process.
        # see: https://www.django-rest-framework.org/api-guide/authentication/#how-authentication-is-determined
        if not self.user:
            # this is the expected case, where the request object is missing the user and therefore
            # the AccountMixin has not set user nor account.
            self.user = SmarterTokenAuthentication.get_user_from_request(request)
        request.user = self.user  # type: ignore[assignment]

        if self.smarter_request is None:
            raise SmarterConfigurationError(
                f"{self.formatted_class_name}.smarter_request request object is not set. This should not happen."
            )
        if not self.ready:
            logger.warning(
                f"{self.formatted_class_name}.initial() is not in a ready state. This might affect some operations."
            )

        # Manifest parsing and broker instantiation are lazy implementations.
        # So for now, we'll only set the private class variable _manifest_data
        # from the request body, and then we'll leave it to the child views to
        # decide if/when to actually parse the manifest and instantiate the broker.

        # if the command is 'chat', then the raw prompt text
        # or the encoded file attachment data will be in the request body.
        # otherwise, the request body should contain manifest text.
        if self.command == SmarterJournalCliCommands.CHAT:
            self._prompt = self.data if isinstance(self.data, str) else None
            self._manifest_kind = SAMKinds.CHAT.value
        else:
            self._manifest_data = self.data if isinstance(self.data, dict) else None

        # Parse the query string parameters from the request into a dictionary.
        # This is used to pass additional parameters to the child view's post method.
        self._manifest_name = self.params.get("name", None) if self.params else kwargs.get("name", None)

        user_agent = request.headers.get("User-Agent", "")
        if "Go-http-client" not in user_agent:
            logger.warning("The User-Agent is not a Go lang application: %s", user_agent)

        kind = kwargs.get("kind", None)
        if kind:
            self._manifest_kind = Brokers.get_broker_kind(kind)
            if not self.manifest_kind:
                return SmarterJournaledJsonErrorResponse(
                    request=request,
                    thing=self.manifest_kind,
                    command=self.command,
                    e=SAMBadRequestError(
                        f"Unsupported manifest kind: {self.manifest_kind}. should be one of {SAMKinds.all_values()}"
                    ),
                    status=HTTPStatus.BAD_REQUEST.value,
                    stack_trace=traceback.format_exc(),
                )
        logger.info(
            "CliBaseApiView().initial() - finished initializing view for request: %s, user: %s",
            url,
            request.user.username if request and getattr(request, "user", None) and getattr(request.user, "is_authenticated", False) else "Anonymous",  # type: ignore[assignment]
        )

    # pylint: disable=too-many-return-statements,too-many-branches
    def dispatch(self, request: Request, *args, **kwargs):
        """
        Dispatch the request to the appropriate handler method.

        This method is a core part of the Django REST Framework (DRF) view lifecycle. It is called automatically by DRF when an HTTP request is received and is responsible for routing the request to the correct handler method (such as ``get()``, ``post()``, ``put()``, etc.) based on the HTTP method of the request.

        In DRF, the ``dispatch()`` method performs several critical functions:

        - It determines which handler method should process the request.
        - It manages the execution of middleware and mixins.
        - It handles exceptions that may be raised during request processing.
        - It returns a DRF ``Response`` object to the client.

        In this base class implementation, the primary objective is to provide robust exception handling for all CLI API views. The method attempts to map known exceptions to appropriate HTTP status codes and, where possible, adds additional context to error messages. This ensures that clients receive meaningful and actionable error responses, even if an unexpected error occurs.

        Ideally, child views should handle their own exceptions and return a ``SmarterJournaledJsonErrorResponse`` or similar structured response. However, this base implementation acts as a safety net, catching any unhandled exceptions and returning a generic error message along with a bug report URL for further troubleshooting.

        Signals are emitted to indicate the completion or failure of API requests, which can be used for logging, auditing, or triggering other side effects.

        Parameters
        ----------
        request : Request
            The HTTP request object provided by DRF, containing all request data, headers, and user context.

        *args
            Additional positional arguments passed to the view.

        **kwargs
            Additional keyword arguments passed to the view, often including URL parameters.

        Returns
        -------
        Response
            A DRF ``Response`` object representing the result of the request, or an error response if an exception was raised.

        Notes
        -----
        - This method is a critical integration point with DRF's request/response lifecycle.
        - Exception mapping is comprehensive, covering both application-specific and DRF exceptions.
        - Unhandled exceptions are logged and reported with a generic message and bug report instructions.
        - Signals are used for observability and integration with other parts of the application.

        See Also
        --------
        https://www.django-rest-framework.org/api-guide/views/#view-methods
            DRF documentation on view methods and the dispatch process.
        """
        response = None
        try:
            url = smarter_build_absolute_uri(request)
            logger.info("%s.dispatch() - called for request: %s", self.formatted_class_name, url)
            response = super().dispatch(request, *args, **kwargs)
            logger.info(
                "%s.dispatch() - finished processing request: %s, user_profile: %s, account: %s",
                self.formatted_class_name,
                url,
                self.user_profile if self.user_profile else None,
                self.account if self.account else None,
            )
            api_request_completed.send(sender=self.__class__, instance=self, request=request, response=response)
            return response
        # pylint: disable=broad-except
        except Exception as e:
            api_request_failed.send(sender=self.__class__, instance=self, request=request, response=response)
            status: int = HTTPStatus.INTERNAL_SERVER_ERROR.value
            description_override: Optional[str] = None

            if type(e) in (SAMBrokerErrorNotImplemented,):
                status = HTTPStatus.NOT_IMPLEMENTED.value
            elif type(e) in (SAMBrokerErrorNotReady,):
                status = HTTPStatus.SERVICE_UNAVAILABLE.value
            elif type(e) in (SAMBrokerErrorNotFound,):
                status = HTTPStatus.NOT_FOUND.value
            elif type(e) in (SAMBrokerReadOnlyError,):
                status = HTTPStatus.METHOD_NOT_ALLOWED.value
            elif type(e) in (
                SmarterAPIV1CLIViewErrorNotAuthenticated,
                SmarterInvalidApiKeyError,
                SmarterTokenError,
                NotAuthenticated,
                AuthenticationFailed,
                AttributeError,  # can be raised by a django admin decorator if request or request.user is None
            ):
                status = HTTPStatus.FORBIDDEN.value
            elif type(e) in (
                SAMBrokerError,
                SmarterValueError,
                SmarterIlligalInvocationError,
                SmarterBusinessRuleViolation,
            ):
                status = HTTPStatus.BAD_REQUEST.value
            elif type(e) in (
                SmarterChatappViewError,
                SmarterChatBotException,
                DocsError,
                SmarterPluginError,
                SmarterConfigurationError,
                SmarterAWSError,
                KubernetesHelperException,
                SmarterJournalEnumException,
                SmarterException,
            ):
                status = HTTPStatus.INTERNAL_SERVER_ERROR.value

            if status in (
                HTTPStatus.INTERNAL_SERVER_ERROR.value,
                HTTPStatus.BAD_REQUEST.value,
                HTTPStatus.SERVICE_UNAVAILABLE.value,
            ):
                # if the error is not a known error, then we should
                # log the error and return a generic error message with bug report instructions.
                logger.error(
                    "%s.dispatch() - %s: %s",
                    self.formatted_class_name,
                    type(e),
                    str(e),
                )
                description_override = f"{type(e)}: " + BUG_REPORT + " " + str(e)

            return SmarterJournaledJsonErrorResponse(
                request=request,
                thing=self.manifest_kind,
                command=self.command,
                e=e,
                status=status,
                stack_trace=traceback.format_exc(),
                description=description_override,
            )
