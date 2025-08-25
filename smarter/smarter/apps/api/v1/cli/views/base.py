"""Smarter API command-line interface Base class API view"""

import json
import logging
import re
import traceback
from http import HTTPStatus
from typing import Any, Optional, Type

from rest_framework.exceptions import NotAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView

from smarter.apps.api.signals import api_request_completed, api_request_initiated
from smarter.apps.api.v1.cli.brokers import Brokers
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.api.v1.manifests.version import SMARTER_API_VERSION
from smarter.apps.chatbot.exceptions import SmarterChatBotException
from smarter.apps.docs.views.base import DocsError
from smarter.apps.plugin.plugin.base import SmarterPluginError
from smarter.apps.prompt.views import SmarterChatappViewError
from smarter.common.const import (
    SMARTER_BUG_REPORT_URL,
    SMARTER_CUSTOMER_SUPPORT_EMAIL,
    SMARTER_IS_INTERNAL_API_REQUEST,
)
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
from smarter.common.utils import mask_string, smarter_build_absolute_uri
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


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING) and level >= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

BUG_REPORT = (
    "Encountered an unexpected error. "
    f"This is a bug. Please contact {SMARTER_CUSTOMER_SUPPORT_EMAIL} "
    f"and/or report to {SMARTER_BUG_REPORT_URL}."
)


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
    Smarter API command-line interface Base class API view. Handles
    common tasks for all /api/v1/cli views:
    - Authenticates the request using either knox TokenAuthentication
      or Django SessionAuthentication.
    - Initializes the SAMLoader and AbstractBroker instances.
    - Resolves the manifest kind and broker for the yaml manifest document.
    - Sets the user profile for the request.

    We want to take care of as
    much housekeeping as possible in the base class. This includes
    setting following attributes:

    - manifest_name: the name identifier of the manifest could be passed
        from insider the raw manifest data, or it could be passed as part of a url.

    - manifest: the http request body might contain raw manifest text
        in yaml or json format. The manifest text is passed to the SAMLoader that will load,
        and partially validate and parse the manifest. This is then used to
        fully initialize a Pydantic manifest model. The Pydantic manifest
        model will be passed to a AbstractBroker for the manifest 'kind', which
        implements the broker service pattern for the underlying object.

    - kind: the kind of the manifest is used to identify the broker that will

    - user/account: the user, account and user_profile are all derived from the
        authenticated user in the Django request object.

    - command: the command is derived from the request path. The command is
        used to determine the type of operation that the view should perform.
        For example, if the url path is '/api/v1/cli/apply/', then the command
        will be SmarterJournalCliCommands.APPLY.

    - broker: the broker is a class that implements the broker service pattern.
        It provides a service interface that 'brokers' the http request for the
        underlying object that provides the object-specific service (create, update, get, delete, etc).
    """

    authentication_classes = (SmarterTokenAuthentication,)
    permission_classes = (SmarterAuthenticatedPermissionClass,)

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
        SmarterRequestMixin.__init__(self, request, *args, **kwargs)
        super().__init__(*args, **kwargs)

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the class name in a formatted string
        along with the name of this mixin.
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
        """
        logger.info(
            "%s.setup() - called for request: %s", self.formatted_class_name, smarter_build_absolute_uri(request)
        )
        super().setup(request, *args, **kwargs)
        logger.info(
            "%s.setup() - view for request: %s, user: %s is_authenticated: %s",
            self.formatted_class_name,
            smarter_build_absolute_uri(request),
            request.user.username if request.user else "Anonymous",  # type: ignore[assignment]
            request.user.is_authenticated,
        )
        # experiment: we want to ensure that the request object is
        # initialized before we call the SmarterRequestMixin.
        SmarterRequestMixin.__init__(self, request=request, *args, **kwargs)

        # note: setup() is the earliest point in the request lifecycle where we can
        # send signals.
        api_request_initiated.send(sender=self.__class__, instance=self, request=request)
        logger.info(
            "CliBaseApiView().setup() - finished view for request: %s, user: %s, self.user: %s is_authenticated: %s",
            smarter_build_absolute_uri(request),
            request.user.username if request.user else "Anonymous",  # type: ignore[assignment]
            self.user_profile,
            request.user.is_authenticated,
        )

    def initial(self, request: Request, *args, **kwargs):
        """
        Initialize the view. This is called by DRF after setup() but before dispatch().

        This is the earliest point in the DRF view lifecycle where the request object is available.
        Up to this point our SmarterRequestMixin, and AccountMixin classes are only partially
        initialized. This method takes care of the rest of the initialization.
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
                request.user.is_authenticated,
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
        Dispatch the request to the appropriate handler method. This is
        called by the Django REST framework when a request is received.
        It is responsible for handling the request and returning a
        response.

        Our only objective in the base class is to accurately
        map exceptions to HTTP status codes, and where possible
        add context to the error message.

        Ideally, the child views have handled their own exceptions
        and returned their own SmarterJournaledJson response. Here
        we're just trying to catch any unhandled exceptions and
        return a generic error message with a bug report URL.
        """
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
