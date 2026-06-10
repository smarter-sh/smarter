# pylint: disable=W0611
"""LLMClient api/v1/llm_clients base view, for invoking a LLMClient."""

import traceback
from http import HTTPStatus
from typing import List, Optional
from urllib.parse import ParseResult, urlparse

from django.contrib.auth.models import User
from django.core.handlers.asgi import ASGIRequest
from django.http import HttpResponseNotAllowed, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response

from smarter.apps.account.models.user_profile import UserProfile
from smarter.apps.llm_client.exceptions import SmarterLLMClientException
from smarter.apps.llm_client.models import (
    LLMClient,
    LLMClientFunctions,
    LLMClientHelper,
    LLMClientPlugin,
)
from smarter.apps.llm_client.serializers import LLMClientSerializer
from smarter.apps.llm_client.signals import llm_client_called
from smarter.apps.plugin.plugin.base import PluginBase
from smarter.apps.prompt.models import Chat, ChatHelper
from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterHttpMethods
from smarter.common.utils import is_authenticated_request
from smarter.lib import logging
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import (
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
    SmarterJournalThings,
)
from smarter.lib.journal.http import (
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
)

base_logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING])
logger = base_logger


# pylint: disable=too-many-instance-attributes
@method_decorator(csrf_exempt, name="dispatch")
class LLMClientApiBaseViewSet(SmarterAuthenticatedNeverCachedWebView):
    """
    Base viewset for all LLMClient API endpoints.

    This class serves as the foundational viewset for all llm_client-related APIs in the Smarter platform,
    including prompt completions that leverage the Smarter LLM Tool Call Plugin architecture.

    **Key Responsibilities:**

    - **API Key Authentication and Request Validation:**
      Enforces authentication for all API requests, rejecting those without a valid API key.

    - **Lifecycle Management:**
      Handles initialization of Account, LLMClient, LLMClientHelper, and ChatHelper objects, and manages request dispatching
      and routing to the appropriate handler methods.

    - **Plugin Discovery and Extensibility:**
      Discovers and initializes plugins for llm_client extensibility, supporting the Smarter LLM Tool Call Plugin architecture.

    - **Logging and Observability:**
      Provides robust logging and observability for all major lifecycle events, including error handling.

    **Django Integration:**

    - Subclasses Django's view-template system (not DRF), participating in the standard request/response lifecycle.
    - Overrides and extends methods such as ``setup()``, ``dispatch()``, ``get()``, and ``post()`` to provide llm_client-specific logic.
    - CSRF-exempt to support API clients.

    **Prompt Completion & LLM Tool Call Plugins:**

    - This base view is designed to support prompt completion endpoints that utilize Smarter's LLM Tool Call Plugin architecture.
    - Plugins can be discovered and invoked as part of the llm_client's response generation, enabling extensible and dynamic tool use.

    **Examples:**

        - ``https://customer-support.3141-5926-5359.api.example.com/``
        - ``https://platform.smarter/workbench/example/``
        - ``https://platform.smarter/api/v1/workbench/1/chat/``

    **Notes:**

    - Intended to be subclassed by concrete llm_client API views.
    - Provides robust error handling and logging for all major operations.
    - Authentication is enforced by default.
    - CSRF-exempt for API compatibility.

    **See Also:**
        - Django REST Framework View lifecycle: https://www.django-rest-framework.org/api-guide/views/#view-initialization
        - SmarterRequestMixin for request context management.
        - LLMClientHelper and ChatHelper for llm_client and chat session logic.
        - Smarter LLM Tool Call Plugin architecture documentation.
    """

    _llm_client_id: Optional[int] = None
    _llm_client_helper: Optional[LLMClientHelper] = None
    _chat_helper: Optional[ChatHelper] = None
    _name: Optional[str] = None

    http_method_names: list[str] = ["get", "post", "options"]
    plugins: Optional[List[PluginBase]] = None
    functions: Optional[list[str]] = None

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

    @property
    def llm_client_id(self):
        """
        Returns the llm_client ID.

        :return: The llm_client ID.
        :rtype: Optional[int]
        """
        return self._llm_client_id

    @property
    def chat_helper(self) -> ChatHelper:
        """
        Returns the ChatHelper instance.

        Lazily initializes the ChatHelper if it hasn't been created yet.

        :return: The ChatHelper instance.
        :rtype: ChatHelper
        """
        if self._chat_helper:
            return self._chat_helper

        if self.session_key or self.llm_client:
            self._chat_helper = ChatHelper(
                request=self.smarter_request, session_key=self.session_key, llm_client=self.llm_client
            )
            if self._chat_helper:
                self.helper_logger(
                    f"{self.formatted_class_name} initialized with chat: {self.chat_helper.chat}, llm_client: {self.llm_client}"
                )
        else:
            raise SmarterLLMClientException(
                f"ChatHelper not found. request={self.smarter_request} name={self.name}, llm_client_id={self.llm_client_id}, session_key={self.session_key}, user_profile={self.user_profile}"
            )

        return self._chat_helper

    @property
    def llm_client_helper(self) -> Optional[LLMClientHelper]:
        """
        Returns the LLMClientHelper instance.

        Lazily initializes the LLMClientHelper if it hasn't been created yet.

        :return: The LLMClientHelper instance.
        :rtype: Optional[LLMClientHelper]
        """
        if self._llm_client_helper:
            return self._llm_client_helper
        # ensure that we have some combination of properties that can identify an llm_client
        if not (self.url or self.llm_client_id or (self.user_profile and self.name)):
            return None
        try:
            self._llm_client_helper = LLMClientHelper(
                request=self.smarter_request,
                name=self.name,
                llm_client_id=self.llm_client_id,
                # SmarterRequestMixin should have set these properties
                session_key=self.session_key,
                # and these, for AccountMixin,
                account=self.account,
                user=self.user,
                user_profile=self.user_profile,
            )
        # smarter.apps.llm_client.models.LLMClient.DoesNotExist: LLMClient matching query does not exist.
        except LLMClient.DoesNotExist as e:
            raise LLMClient.DoesNotExist(
                f"LLMClient not found. request={self.smarter_request} name={self.name}, llm_client_id={self.llm_client_id}, session_key={self.session_key}, user_profile={self.user_profile}"
            ) from e

        self._llm_client_id = self._llm_client_helper.llm_client_id
        if self._llm_client_id:
            logger.debug(
                "%s: %s initialized LLMClientHelper with id: %s, url: %s",
                self.formatted_class_name,
                self._llm_client_helper,
                self._llm_client_id,
                self._url,
            )
        if self._llm_client_helper:
            logger.debug(
                "%s: %s LLMClientHelper reinitializing user_profile: %s",
                self.formatted_class_name,
                self._llm_client_helper,
                self.user_profile,
            )
            self._url = urlparse(self._llm_client_helper.url)  # type: ignore
            self._user = self._llm_client_helper.user
            self._account = self._llm_client_helper.account
            self._user_profile = self._llm_client_helper.user_profile
        logger.debug(
            "%s: %s initialized with url: %s id: %s",
            self.formatted_class_name,
            self._llm_client_helper,
            self.url,
            self.llm_client_id,
        )
        return self._llm_client_helper

    @property
    def name(self):
        """
        Returns the name of the llm_client.

        :return: The name of the llm_client.
        :rtype: Optional[str]
        """
        if self._name:
            return self._name
        self._name = self._llm_client_helper.name if self._llm_client_helper else None

    @property
    def llm_client(self):
        """
        Returns the LLMClient instance.

        :return: The LLMClient instance.
        :rtype: Optional[LLMClient]
        """
        return self.llm_client_helper.llm_client if self.llm_client_helper else None

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the class name in a formatted string.

        along with the name of this mixin.

        :return: Formatted class name string.
        :rtype: str
        """
        class_name = f"{__name__}.{LLMClientApiBaseViewSet.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    @property
    def url(self) -> Optional[ParseResult]:
        """
        Returns the URL of the llm_client.

        :return: The URL of the llm_client.
        :rtype: Optional[ParseResult]
        """
        try:
            return self._url
        # pylint: disable=W0718
        except Exception as e:
            logger.warning("%s: Error getting url: %s", self.formatted_class_name, e)

    @property
    def is_web_platform(self):
        """
        Determine if the request is from the web platform domain.

        :return: True if the request is from the web platform domain, False otherwise.
        :rtype: bool
        """
        host = self.smarter_request.get_host() if self.smarter_request else ""
        if host in smarter_settings.environment_platform_domain:
            return True
        return False

    def helper_logger(self, message: str):
        """
        Create a log entry.

        :param message: The message to log.
        :type message: str
        """
        logger.debug("%s: %s", self.formatted_class_name, message)

    def setup(self, request: ASGIRequest, *args, **kwargs):
        """
        Set up the LLMClient API base viewset for request processing.

        This method is called as part of the Django REST Framework (DRF) view lifecycle,
        immediately after the view instance is created and before the request is dispatched
        to the appropriate handler method (such as ``get()`` or ``post()``).

        The primary responsibilities of this method are to:

        - Initialize the :class:`SmarterRequestMixin` with the current request and any additional arguments.
        - Prepare and set up the :class:`LLMClientHelper` and :class:`ChatHelper` instances, which are used
          throughout the request lifecycle for llm_client-specific logic and chat session management.
        - Log key setup events for observability and debugging.

        Parameters
        ----------
        request : ASGIRequest
            The HTTP request object provided by Django, containing all request data, headers, and user context.

        *args
            Additional positional arguments passed to the view.

        **kwargs
            Additional keyword arguments passed to the view, often including URL parameters.

        Notes
        -----
        - This method is a critical integration point with DRF's request/response lifecycle.
        - It ensures that all necessary context and helper objects are available before
          the main handler methods are called.
        - Subclasses may override this method to provide additional setup logic, but should
          always call ``super().setup()`` to preserve base functionality.

        See Also
        --------
        - Django REST Framework View lifecycle: https://www.django-rest-framework.org/api-guide/views/#view-initialization
        - SmarterRequestMixin for request context management.
        - LLMClientHelper and ChatHelper for llm_client and chat session logic.
        """
        logger.debug(
            "%s.setup() - request: %s, args: %s, kwargs: %s",
            self.formatted_class_name,
            self.smarter_build_absolute_uri(request),
            args,
            kwargs,
        )
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request: ASGIRequest, *args, name: Optional[str] = None, **kwargs):
        """
        Dispatch method for the LLMClient API base viewset.

        This method is invoked as part of the Django REST Framework (DRF) view lifecycle.
        It is responsible for preparing the viewset for request processing, including
        initializing the LLMClientHelper and ChatHelper instances, setting up the request context,
        and logging relevant information for observability and debugging.

        The dispatch method performs the following key actions:

        - Extracts and sets the llm_client ID from the URL parameters, if present.
        - Initializes the LLMClient and Account context for the request.
        - Validates the existence and readiness of the LLMClientHelper and LLMClient instances.
        - Handles error conditions such as missing or invalid llm_client configuration, returning
          appropriate HTTP error responses.
        - Loads and attaches plugins for the llm_client, if available.
        - Emits signals and logs key request metadata for auditing and debugging.
        - Calls the parent class's dispatch method to continue the DRF request/response lifecycle.

        Parameters
        ----------
        request : ASGIRequest
            The HTTP request object provided by Django, containing all request data, headers, and user context.

        *args
            Additional positional arguments passed to the view.

        name : Optional[str]
            The name of the llm_client, if provided as a URL parameter.

        **kwargs
            Additional keyword arguments passed to the view, often including URL parameters.

        Returns
        -------
        JsonResponse or HttpResponse
            A Django JsonResponse or HttpResponse object representing the result of the request,
            or an error response if initialization fails.

        Notes
        -----
        - This method is a critical integration point with DRF's request/response lifecycle.
        - It ensures that all necessary context, helpers, and plugins are available before
          the main handler methods are called.
        - Subclasses may override this method to provide additional dispatch logic, but should
          always call ``super().dispatch()`` to preserve base functionality.

        See Also
        --------
        - Django REST Framework View dispatch: https://www.django-rest-framework.org/api-guide/views/#view-methods
        - LLMClientHelper and ChatHelper for llm_client and chat session logic.
        """
        self._llm_client_id = kwargs.get("llm_client_id")
        if self._llm_client_id:
            kwargs.pop("llm_client_id")
        if self.llm_client and self.llm_client.user_profile:
            self._user_profile = self.llm_client.user_profile
            self._account = self.llm_client.user_profile.account
            self._user = self.llm_client.user_profile.user
            logger.debug(
                "%s.dispatch() - reinitializing user, account, and user_profile from llm_client.user_profile: %s",
                self.formatted_class_name,
                self.llm_client.user_profile,
            )
        else:
            self._name = self._name or name
        if not self.llm_client:
            logger.warning(
                "Could not initialize LLMClientHelper url: %s, name: %s, user: %s, account: %s, id: %s",
                self.url,
                self.name,
                self.user,
                self.account,
                self.llm_client_id,
            )
            logger.debug(
                "%s.dispatch() - not found request: %s, args: %s, kwargs: %s",
                self.formatted_class_name,
                self.smarter_build_absolute_uri(request),
                args,
                kwargs,
            )
            return JsonResponse({}, status=HTTPStatus.NOT_FOUND.value)

        logger.debug("%s.dispatch() - url=%s", self.formatted_class_name, self.url)
        logger.debug("%s.dispatch() - id=%s", self.formatted_class_name, self.llm_client_id)
        logger.debug("%s.dispatch() - name=%s", self.formatted_class_name, self.name)
        logger.debug("%s.dispatch() - account=%s", self.formatted_class_name, self.account)
        logger.debug("%s.dispatch() - llm_client=%s", self.formatted_class_name, self.llm_client)
        logger.debug("%s.dispatch() - user=%s", self.formatted_class_name, request.user)
        logger.debug("%s.dispatch() - method=%s", self.formatted_class_name, request.method)
        logger.debug("%s.dispatch() - body=%s", self.formatted_class_name, self.data)
        logger.debug("%s.dispatch() - headers=%s", self.formatted_class_name, request.META)

        if not self.llm_client_helper:
            raise SmarterLLMClientException(
                f"LLMClientHelper not found. request={self.smarter_request} name={self.name}, llm_client_id={self.llm_client_id}, session_key={self.session_key}, user_profile={self.user_profile}"
            )
        if not self.llm_client_helper.ready:
            data = {
                "data": {
                    "error": {
                        "message": "Could not initialize LLMClient object.",
                        "account": self.account.account_number if self.account else None,
                        "llm_client": LLMClientSerializer(self.llm_client).data if self.llm_client else None,
                        "user": self.user.username if self.user else None,
                        "name": self.llm_client_helper.name,
                        "url": self.llm_client_helper.url,
                    },
                },
            }
            logger.debug("%s.dispatch() - LLMClientHelper not ready", self.formatted_class_name)
            return JsonResponse(data=data, status=HTTPStatus.BAD_REQUEST.value)
        if self.llm_client_helper.is_authentication_required and not is_authenticated_request(request):
            data = {"message": "Forbidden. Please provide a valid API key."}
            logger.debug("%s.dispatch() - Authentication required", self.formatted_class_name)
            return JsonResponse(data=data, status=HTTPStatus.FORBIDDEN.value)

        self.plugins = LLMClientPlugin().plugins(llm_client=self.llm_client)
        self.functions = LLMClientFunctions().functions(llm_client=self.llm_client)

        if self.llm_client_helper.is_llm_client:
            logger.debug("%s.dispatch(): account=%s", self.formatted_class_name, self.account)
            logger.debug("%s.dispatch(): llm_client=%s", self.formatted_class_name, self.llm_client)
            logger.debug("%s.dispatch(): user=%s", self.formatted_class_name, self.user)
            logger.debug("%s.dispatch(): plugins=%s", self.formatted_class_name, self.plugins)
            logger.debug("%s.dispatch(): functions=%s", self.formatted_class_name, self.functions)
            logger.debug("%s.dispatch(): name=%s", self.formatted_class_name, self.name)
            logger.debug("%s.dispatch(): data=%s", self.formatted_class_name, self.data)
            if self.session_key:
                logger.debug("%s.dispatch(): session_key=%s", self.formatted_class_name, self.session_key)
                logger.debug("%s.dispatch(): chat_helper=%s", self.formatted_class_name, self.chat_helper)

        if self.llm_client_helper.is_llm_client and self.chat_helper:
            llm_client_called.send(
                sender=self.__class__,
                llm_client=self.llm_client,
                request=request,
                data=self.data,
                args=args,
                kwargs=kwargs,
            )

        return super().dispatch(request, *args, **kwargs)

    def options(self, request, *args, **kwargs):
        """
        OPTIONS request handler for the Smarter Chat API.

        Sets CORS headers to allow cross-origin requests from the Smarter environment URL.

        :param request: The HTTP request object.
        :type request: ASGIRequest
        """
        logger.debug(
            "%s.options(): url=%s",
            self.formatted_class_name,
            self.llm_client_helper.url if self.llm_client_helper else "(Missing LLMClientHelper.url)",
        )
        response = Response()
        response["Access-Control-Allow-Origin"] = smarter_settings.environment_url
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "origin, content-type, accept"
        return response

    # pylint: disable=W0613
    def get(self, request, *args, name: Optional[str] = None, **kwargs):
        """
        GET request handler for the Smarter Chat API.

        Currently, GET requests are not supported and will return a message indicating that POST should be used
        instead.

        :param request: The HTTP request object.
        :type request: ASGIRequest
        :return: A JsonResponse indicating that GET is not supported.
        :rtype: JsonResponse
        """

        return HttpResponseNotAllowed(permitted_methods=[SmarterHttpMethods.POST])

    # pylint: disable=W0613
    def post(self, request, *args, name: Optional[str] = None, **kwargs):
        """
        POST request handler for the Smarter Chat API.

        This method processes POST requests to the llm_client API endpoint. It determines which
        LLMClient instance to use based on the request's host, supporting both default API domains
        and custom domains. The logic ensures that the correct LLMClient is selected for each request,
        and that all necessary context and helpers are available for downstream processing.

        Hostname Resolution
        -------------------
        The LLMClient instance is determined by parsing the request host. There are two supported formats:

        1. **URL with default API domain**
            Example: ``https://customer-support.3141-5926-5359.api.example.com/llm-client/``
            - ``customer-support``: The llm_client's name.
            - ``3141-5926-5359``: The llm_client's account number.
            - ``api.example.com``: The default API domain.

        2. **URL with custom domain**
            Example: ``https://api.example.com/llm-client/``
            - ``api.example.com``: The llm_client's custom domain.
            - The custom domain must be verified (``LLMClientCustomDomain.is_verified == True``).

        The LLMClient instance hostname is determined by:
        ``llm_client.hostname == llm_client.custom_domain or llm_client.default_host``

        Processing Steps
        ----------------
        - Logs key request and context information for observability.
        - Validates that a LLMClient instance is available; returns an error response if not found.
        - Retrieves the appropriate chat provider handler for the LLMClient.
        - Ensures a valid ChatHelper instance is available; returns an error response if not found.
        - Invokes the chat provider handler with the chat session, request data, plugins, and user context.
        - Wraps the response in a ``SmarterJournaledJsonResponse`` for consistent API output.

        Parameters
        ----------
        request : ASGIRequest
            The HTTP request object provided by Django, containing all request data, headers, and user context.

        *args
            Additional positional arguments passed to the view.

        name : Optional[str]
            The name of the llm_client, if provided as a URL parameter.

        **kwargs
            Additional keyword arguments passed to the view, often including URL parameters.

        Returns
        -------
        SmarterJournaledJsonResponse
            A structured JSON response containing the result of the chat operation, or an error response
            if the LLMClient or ChatHelper could not be initialized.

        Notes
        -----
        - This method is a critical integration point for llm_client conversations in the Smarter platform.
        - It enforces domain-based routing and robust error handling for missing or invalid llm_client context.
        - The response format is standardized for journaling and auditing purposes.

        See Also
        --------
        - Django REST Framework APIView: https://www.django-rest-framework.org/api-guide/views/
        - SmarterJournaledJsonResponse for response structure.
        - LLMClientHelper and ChatHelper for llm_client and chat session logic.
        """

        # pylint: disable=C0415
        from smarter.apps.provider.services.text_completion.providers import (
            SmarterChatHandlerProtocol,
            smarter_compatible_client,
        )

        logger.debug(
            "%s.post() - provider=%s", self.formatted_class_name, self.llm_client.provider if self.llm_client else None
        )
        logger.debug("%s.post() - data=%s", self.formatted_class_name, self.data)
        logger.debug("%s.post() - account: %s - %s", self.formatted_class_name, self.account, self.account_number)
        logger.debug("%s.post() - user: %s", self.formatted_class_name, self.user)
        logger.debug(
            "%s.post() - chat: %s",
            self.formatted_class_name,
            self.chat_helper.chat.user_profile if self.chat_helper and self.chat_helper.chat else None,
        )
        logger.debug("%s.post() - llm_client: %s", self.formatted_class_name, self.llm_client)
        logger.debug("%s.post() - plugins: %s", self.formatted_class_name, self.plugins)

        if not self.llm_client:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                e=LLMClient.DoesNotExist(
                    f"LLMClient not found. request={self.smarter_request} name={self.name}, llm_client_id={self.llm_client_id}, session_key={self.session_key}, user_profile={self.user_profile}"
                ),
                safe=False,
                thing=SmarterJournalThings(SmarterJournalThings.LLM_CLIENT),
                command=SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT),
                status=HTTPStatus.NOT_FOUND.value,
                stack_trace=traceback.format_exc(),
            )
        handler: SmarterChatHandlerProtocol = smarter_compatible_client.get_smarter_handler(
            request=request, provider_name=self.llm_client.provider
        )
        if not self.chat_helper:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                e=Chat.DoesNotExist(
                    f"ChatHelper not found. request={self.smarter_request} name={self.name}, llm_client_id={self.llm_client_id}, session_key={self.session_key}, user_profile={self.user_profile}"
                ),
                safe=False,
                thing=SmarterJournalThings(SmarterJournalThings.LLM_CLIENT),
                command=SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT),
                status=HTTPStatus.NOT_FOUND.value,
                stack_trace=traceback.format_exc(),
            )
        if not self.chat_helper.chat:
            raise SmarterLLMClientException(
                f"Chat not found. This is a bug. request={self.smarter_request} name={self.name}, llm_client_id={self.llm_client_id}, session_key={self.session_key}, user_profile={self.user_profile}"
            )
        if not self.data:
            raise SmarterLLMClientException(
                f"POST data is empty. request={self.smarter_request} name={self.name}, llm_client_id={self.llm_client_id}, session_key={self.session_key}, user_profile={self.user_profile}"
            )
        # RequestMixin.data is more relaxed than the provider expects, so we validate here
        if not isinstance(self.data, (dict, list)):
            raise SmarterLLMClientException(
                f"POST data is not a dict or list. request={self.smarter_request} name={self.name}, llm_client_id={self.llm_client_id}, session_key={self.session_key}, user_profile={self.user_profile}, data_type={type(self.data)}"
            )
        # likewise, AccountMixin.user can accept AnonymousUser, but providers expect a real User
        if not isinstance(self.user, User):
            raise SmarterLLMClientException(
                f"User is not a valid User instance. request={self.smarter_request} name={self.name}, llm_client_id={self.llm_client_id}, session_key={self.session_key}, user_profile={self.user_profile}, user_type={type(self.user)}"
            )
        if not isinstance(self.user_profile, UserProfile):
            raise SmarterLLMClientException(
                f"UserProfile is not a valid UserProfile instance. request={self.smarter_request} name={self.name}, llm_client_id={self.llm_client_id}, session_key={self.session_key}, user_profile={self.user_profile}, user_profile_type={type(self.user_profile)}"
            )
        response = handler(
            self.user_profile, self.chat_helper.chat, self.data, plugins=self.plugins, functions=self.functions
        )
        response = {
            SmarterJournalApiResponseKeys.DATA: response,
        }
        response = SmarterJournaledJsonResponse(
            request=request,
            data=response,
            command=SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT),
            thing=SmarterJournalThings(SmarterJournalThings.LLM_CLIENT),
            status=HTTPStatus.OK.value,
            safe=False,
        )
        self.helper_logger(f"{self.formatted_class_name} response={response}")
        return response
