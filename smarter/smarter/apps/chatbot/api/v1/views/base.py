# pylint: disable=W0611
"""ChatBot api/v1/chatbots base view, for invoking a ChatBot."""
import logging
import traceback
from http import HTTPStatus
from typing import List, Optional
from urllib.parse import ParseResult, urlparse

from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response

from smarter.apps.chatbot.exceptions import SmarterChatBotException
from smarter.apps.chatbot.models import ChatBot, ChatBotHelper, ChatBotPlugin
from smarter.apps.chatbot.serializers import ChatBotSerializer
from smarter.apps.chatbot.signals import chatbot_called
from smarter.apps.plugin.plugin.base import PluginBase
from smarter.apps.prompt.models import ChatHelper
from smarter.apps.prompt.providers.providers import chat_providers
from smarter.common.conf import settings as smarter_settings
from smarter.common.utils import is_authenticated_request
from smarter.lib.django import waffle
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.django.view_helpers import SmarterNeverCachedWebView
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
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


# pylint: disable=too-many-instance-attributes
@method_decorator(csrf_exempt, name="dispatch")
class ChatBotApiBaseViewSet(SmarterNeverCachedWebView):
    """
    Base viewset for all ChatBot API endpoints.

    This class serves as the foundational viewset for all chatbot-related APIs in the Smarter platform.
    It is designed as a subclass of Django REST Framework (DRF) views, providing common functionality
    and lifecycle management for chatbot API requests.

    Key Responsibilities
    --------------------
    - API key authentication and request validation.
    - Initialization of Account, ChatBot, ChatBotHelper, and ChatHelper objects.
    - Request dispatching and routing to the appropriate handler methods.
    - Plugin discovery and initialization for chatbot extensibility.
    - Logging and observability for all major lifecycle events.

    DRF Integration
    ---------------
    As a subclass of DRF's view system, this base viewset participates in the standard DRF request/response
    lifecycle. It overrides and extends methods such as ``setup()``, ``dispatch()``, ``get()``, and ``post()``
    to provide chatbot-specific logic while maintaining compatibility with DRF's middleware, authentication,
    and response handling mechanisms.

    Examples
    --------
    Example API endpoints using this base viewset:

    - ``https://customer-support.3141-5926-5359.api.smarter.sh/``
    - ``https://platform.smarter/workbench/example/``
    - ``https://platform.smarter/api/v1/workbench/1/chat/``

    Notes
    -----
    - This class is intended to be subclassed by concrete chatbot API views.
    - It provides robust error handling and logging for all major operations.
    - Authentication is enforced by default, and requests without a valid API key will be rejected.
    - The viewset is CSRF-exempt to support API clients.

    :see also: `Django REST Framework ViewSets <https://www.django-rest-framework.org/api-guide/viewsets/>`__

    """

    _chatbot_id: Optional[int] = None
    _chatbot_helper: Optional[ChatBotHelper] = None
    _chat_helper: Optional[ChatHelper] = None
    _name: Optional[str] = None

    http_method_names: list[str] = ["get", "post", "options"]
    plugins: Optional[List[PluginBase]] = None

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

    @property
    def chatbot_id(self):
        """
        Returns the chatbot ID.

        :return: The chatbot ID.
        :rtype: Optional[int]
        """
        return self._chatbot_id

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

        if self.session_key or self.chatbot:
            self._chat_helper = ChatHelper(
                request=self.smarter_request, session_key=self.session_key, chatbot=self.chatbot
            )
            if self._chat_helper:
                self.helper_logger(
                    f"{self.formatted_class_name} initialized with chat: {self.chat_helper.chat}, chatbot: {self.chatbot}"
                )
        else:
            raise SmarterChatBotException(
                f"ChatHelper not found. request={self.smarter_request} name={self.name}, chatbot_id={self.chatbot_id}, session_key={self.session_key}, user_profile={self.user_profile}"
            )

        return self._chat_helper

    @property
    def chatbot_helper(self) -> Optional[ChatBotHelper]:
        """
        Returns the ChatBotHelper instance.
        Lazily initializes the ChatBotHelper if it hasn't been created yet.

        :return: The ChatBotHelper instance.
        :rtype: Optional[ChatBotHelper]
        """
        if self._chatbot_helper:
            return self._chatbot_helper
        # ensure that we have some combination of properties that can identify a chatbot
        if not (self.url or self.chatbot_id or (self.account and self.name)):
            return None
        try:
            self._chatbot_helper = ChatBotHelper(
                request=self.smarter_request,
                name=self.name,
                chatbot_id=self.chatbot_id,
                # SmarterRequestMixin should have set these properties
                session_key=self.session_key,
                # and these, for AccountMixin,
                account=self.account,
                user=self.user,
                user_profile=self.user_profile,
            )
        # smarter.apps.chatbot.models.ChatBot.DoesNotExist: ChatBot matching query does not exist.
        except ChatBot.DoesNotExist as e:
            raise SmarterChatBotException(
                f"ChatBot not found. request={self.smarter_request} name={self.name}, chatbot_id={self.chatbot_id}, session_key={self.session_key}, user_profile={self.user_profile}"
            ) from e

        self._chatbot_id = self._chatbot_helper.chatbot_id
        if self._chatbot_id:
            logger.info(
                "%s: %s initialized ChatBotHelper with id: %s, url: %s",
                self.formatted_class_name,
                self._chatbot_helper,
                self._chatbot_id,
                self._url,
            )
        if self._chatbot_helper:
            logger.info(
                "%s: %s ChatBotHelper reinitializing user: %s, account: %s",
            )
            self._url = urlparse(self._chatbot_helper.url)  # type: ignore
            self._user = self._chatbot_helper.user
            self._account = self._chatbot_helper.account
        logger.info(
            "%s: %s initialized with url: %s id: %s",
            self.formatted_class_name,
            self._chatbot_helper,
            self.url,
            self.chatbot_id,
        )
        return self._chatbot_helper

    @property
    def name(self):
        """
        Returns the name of the chatbot.

        :return: The name of the chatbot.
        :rtype: Optional[str]
        """
        if self._name:
            return self._name
        self._name = self._chatbot_helper.name if self._chatbot_helper else None

    @property
    def chatbot(self):
        """
        Returns the ChatBot instance.
        :return: The ChatBot instance.
        :rtype: Optional[ChatBot]
        """
        return self.chatbot_helper.chatbot if self.chatbot_helper else None

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the class name in a formatted string
        along with the name of this mixin.

        :return: Formatted class name string.
        :rtype: str
        """
        inherited_class = super().formatted_class_name
        return f"{inherited_class} ChatBotApiBaseViewSet()"

    @property
    def url(self) -> Optional[ParseResult]:
        """
        Returns the URL of the chatbot.

        :return: The URL of the chatbot.
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
        host = self.smarter_request.get_host()
        if host in smarter_settings.environment_platform_domain:
            return True
        return False

    def helper_logger(self, message: str):
        """
        Create a log entry

        :param message: The message to log.
        :type message: str
        """
        logger.info("%s: %s", self.formatted_class_name, message)

    def setup(self, request: WSGIRequest, *args, **kwargs):
        """
        Set up the ChatBot API base viewset for request processing.

        This method is called as part of the Django REST Framework (DRF) view lifecycle,
        immediately after the view instance is created and before the request is dispatched
        to the appropriate handler method (such as ``get()`` or ``post()``).

        The primary responsibilities of this method are to:

        - Initialize the :class:`SmarterRequestMixin` with the current request and any additional arguments.
        - Prepare and set up the :class:`ChatBotHelper` and :class:`ChatHelper` instances, which are used
          throughout the request lifecycle for chatbot-specific logic and chat session management.
        - Log key setup events for observability and debugging.

        Parameters
        ----------
        request : WSGIRequest
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
        - ChatBotHelper and ChatHelper for chatbot and chat session logic.
        """
        logger.info(
            "%s.setup() - request: %s, args: %s, kwargs: %s",
            self.formatted_class_name,
            self.smarter_build_absolute_uri(request),
            args,
            kwargs,
        )
        SmarterRequestMixin.__init__(self, request=request, *args, **kwargs)
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request: WSGIRequest, *args, name: Optional[str] = None, **kwargs):
        """
        Dispatch method for the ChatBot API base viewset.

        This method is invoked as part of the Django REST Framework (DRF) view lifecycle.
        It is responsible for preparing the viewset for request processing, including
        initializing the ChatBotHelper and ChatHelper instances, setting up the request context,
        and logging relevant information for observability and debugging.

        The dispatch method performs the following key actions:

        - Extracts and sets the chatbot ID from the URL parameters, if present.
        - Initializes the ChatBot and Account context for the request.
        - Validates the existence and readiness of the ChatBotHelper and ChatBot instances.
        - Handles error conditions such as missing or invalid chatbot configuration, returning
          appropriate HTTP error responses.
        - Loads and attaches plugins for the chatbot, if available.
        - Emits signals and logs key request metadata for auditing and debugging.
        - Calls the parent class's dispatch method to continue the DRF request/response lifecycle.

        Parameters
        ----------
        request : WSGIRequest
            The HTTP request object provided by Django, containing all request data, headers, and user context.

        *args
            Additional positional arguments passed to the view.

        name : Optional[str]
            The name of the chatbot, if provided as a URL parameter.

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
        - ChatBotHelper and ChatHelper for chatbot and chat session logic.
        """
        self._chatbot_id = kwargs.get("chatbot_id")
        if self._chatbot_id:
            kwargs.pop("chatbot_id")
        if self.chatbot:
            self.account = self.chatbot.account
        else:
            self._name = self._name or name
        if not self.chatbot:
            logger.error(
                "Could not initialize ChatBotHelper url: %s, name: %s, user: %s, account: %s, id: %s",
                self.url,
                self.name,
                self.user,
                self.account,
                self.chatbot_id,
            )
            return JsonResponse({}, status=HTTPStatus.NOT_FOUND.value)

        logger.info("%s.dispatch() - url=%s", self.formatted_class_name, self.url)
        logger.info("%s.dispatch() - id=%s", self.formatted_class_name, self.chatbot_id)
        logger.info("%s.dispatch() - name=%s", self.formatted_class_name, self.name)
        logger.info("%s.dispatch() - account=%s", self.formatted_class_name, self.account)
        logger.info("%s.dispatch() - chatbot=%s", self.formatted_class_name, self.chatbot)
        logger.info("%s.dispatch() - user=%s", self.formatted_class_name, request.user)
        logger.info("%s.dispatch() - method=%s", self.formatted_class_name, request.method)
        logger.info("%s.dispatch() - body=%s", self.formatted_class_name, request.body)
        logger.info("%s.dispatch() - headers=%s", self.formatted_class_name, request.META)

        if not self.chatbot_helper:
            raise SmarterChatBotException(
                f"ChatBotHelper not found. request={self.smarter_request} name={self.name}, chatbot_id={self.chatbot_id}, session_key={self.session_key}, user_profile={self.user_profile}"
            )
        if not self.chatbot_helper.is_valid:
            data = {
                "data": {
                    "error": {
                        "message": "Could not initialize ChatBot object.",
                        "account": self.account.account_number if self.account else None,
                        "chatbot": ChatBotSerializer(self.chatbot).data if self.chatbot else None,
                        "user": self.user.username if self.user else None,
                        "name": self.chatbot_helper.name,
                        "url": self.chatbot_helper.url,
                    },
                },
            }
            self.chatbot_helper.log_dump()
            return JsonResponse(data=data, status=HTTPStatus.BAD_REQUEST.value)
        if self.chatbot_helper.is_authentication_required and not is_authenticated_request(request):
            data = {"message": "Forbidden. Please provide a valid API key."}
            return JsonResponse(data=data, status=HTTPStatus.FORBIDDEN.value)

        self.plugins = ChatBotPlugin().plugins(chatbot=self.chatbot)

        if self.chatbot_helper.is_chatbot:
            logger.info("%s.dispatch(): account=%s", self.formatted_class_name, self.account)
            logger.info("%s.dispatch(): chatbot=%s", self.formatted_class_name, self.chatbot)
            logger.info("%s.dispatch(): user=%s", self.formatted_class_name, self.user)
            logger.info("%s.dispatch(): plugins=%s", self.formatted_class_name, self.plugins)
            logger.info("%s.dispatch(): name=%s", self.formatted_class_name, self.name)
            logger.info("%s.dispatch(): data=%s", self.formatted_class_name, self.data)
            if self.session_key:
                logger.info("%s.dispatch(): session_key=%s", self.formatted_class_name, self.session_key)
                logger.info("%s.dispatch(): chat_helper=%s", self.formatted_class_name, self.chat_helper)

        if self.chatbot_helper.is_chatbot and self.chat_helper:
            chatbot_called.send(sender=self.__class__, chatbot=self.chatbot, request=request, args=args, kwargs=kwargs)

        return super().dispatch(request, *args, **kwargs)

    def options(self, request, *args, **kwargs):
        """
        OPTIONS request handler for the Smarter Chat API.
        Sets CORS headers to allow cross-origin requests from the Smarter environment URL.

        :param request: The HTTP request object.
        :type request: WSGIRequest
        """
        logger.info(
            "%s.options(): url=%s",
            self.formatted_class_name,
            self.chatbot_helper.url if self.chatbot_helper else "(Missing ChatBotHelper.url)",
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
        :type request: WSGIRequest
        :return: A JsonResponse indicating that GET is not supported.
        :rtype: JsonResponse
        """
        url = self.chatbot_helper.url if self.chatbot_helper else self.smarter_build_absolute_uri(request)
        logger.info("%s.get(): url=%s", self.formatted_class_name, url)
        logger.info("%s.get(): headers=%s", self.formatted_class_name, request.META)
        retval = {
            "message": "GET is not supported. Please use POST.",
            "chatbot": self.chatbot.name if self.chatbot else None,
            "mode": self.chatbot.mode(url=self.chatbot_helper.url) if self.chatbot and self.chatbot_helper else None,
            "created": self.chatbot.created_at.isoformat() if self.chatbot else None,
            "updated": self.chatbot.updated_at.isoformat() if self.chatbot else None,
            "plugins": ChatBotPlugin.plugins_json(chatbot=self.chatbot) if self.chatbot else None,
            "account": self.account.account_number if self.account else None,
            "user": self.user.username if self.user else None,
            "meta": self.chatbot_helper.to_json() if self.chatbot_helper else None,
        }
        return JsonResponse(data=retval, status=HTTPStatus.OK.value)

    # pylint: disable=W0613
    def post(self, request, *args, name: Optional[str] = None, **kwargs):
        """
        POST request handler for the Smarter Chat API.

        This method processes POST requests to the chatbot API endpoint. It determines which
        ChatBot instance to use based on the request's host, supporting both default API domains
        and custom domains. The logic ensures that the correct ChatBot is selected for each request,
        and that all necessary context and helpers are available for downstream processing.

        Hostname Resolution
        -------------------
        The ChatBot instance is determined by parsing the request host. There are two supported formats:

        1. **URL with default API domain**
            Example: ``https://customer-support.3141-5926-5359.api.smarter.sh/chatbot/``
            - ``customer-support``: The chatbot's name.
            - ``3141-5926-5359``: The chatbot's account number.
            - ``api.smarter.sh``: The default API domain.

        2. **URL with custom domain**
            Example: ``https://api.smarter.sh/chatbot/``
            - ``api.smarter.sh``: The chatbot's custom domain.
            - The custom domain must be verified (``ChatBotCustomDomain.is_verified == True``).

        The ChatBot instance hostname is determined by:
        ``chatbot.hostname == chatbot.custom_domain or chatbot.default_host``

        Processing Steps
        ----------------
        - Logs key request and context information for observability.
        - Validates that a ChatBot instance is available; returns an error response if not found.
        - Retrieves the appropriate chat provider handler for the ChatBot.
        - Ensures a valid ChatHelper instance is available; returns an error response if not found.
        - Invokes the chat provider handler with the chat session, request data, plugins, and user context.
        - Wraps the response in a ``SmarterJournaledJsonResponse`` for consistent API output.

        Parameters
        ----------
        request : WSGIRequest
            The HTTP request object provided by Django, containing all request data, headers, and user context.

        *args
            Additional positional arguments passed to the view.

        name : Optional[str]
            The name of the chatbot, if provided as a URL parameter.

        **kwargs
            Additional keyword arguments passed to the view, often including URL parameters.

        Returns
        -------
        SmarterJournaledJsonResponse
            A structured JSON response containing the result of the chat operation, or an error response
            if the ChatBot or ChatHelper could not be initialized.

        Notes
        -----
        - This method is a critical integration point for chatbot conversations in the Smarter platform.
        - It enforces domain-based routing and robust error handling for missing or invalid chatbot context.
        - The response format is standardized for journaling and auditing purposes.

        See Also
        --------
        - Django REST Framework APIView: https://www.django-rest-framework.org/api-guide/views/
        - SmarterJournaledJsonResponse for response structure.
        - ChatBotHelper and ChatHelper for chatbot and chat session logic.
        """

        logger.info(
            "%s.post() - provider=%s", self.formatted_class_name, self.chatbot.provider if self.chatbot else None
        )
        logger.info("%s.post() - data=%s", self.formatted_class_name, self.data)
        logger.info("%s.post() - account: %s - %s", self.formatted_class_name, self.account, self.account_number)
        logger.info("%s.post() - user: %s", self.formatted_class_name, self.user)
        logger.info(
            "%s.post() - chat: %s",
            self.formatted_class_name,
            self.chat_helper.chat.account.account_number if self.chat_helper and self.chat_helper.chat else None,
        )
        logger.info("%s.post() - chatbot: %s", self.formatted_class_name, self.chatbot)
        logger.info("%s.post() - plugins: %s", self.formatted_class_name, self.plugins)

        if not self.chatbot:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                e=SmarterChatBotException(
                    f"ChatBot not found. request={self.smarter_request} name={self.name}, chatbot_id={self.chatbot_id}, session_key={self.session_key}, user_profile={self.user_profile}"
                ),
                safe=False,
                thing=SmarterJournalThings(SmarterJournalThings.CHATBOT),
                command=SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT),
                status=HTTPStatus.NOT_FOUND.value,
                stack_trace=traceback.format_exc(),
            )
        handler = chat_providers.get_handler(provider=self.chatbot.provider)
        if not self.chat_helper:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                e=SmarterChatBotException(
                    f"ChatHelper not found. request={self.smarter_request} name={self.name}, chatbot_id={self.chatbot_id}, session_key={self.session_key}, user_profile={self.user_profile}"
                ),
                safe=False,
                thing=SmarterJournalThings(SmarterJournalThings.CHATBOT),
                command=SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT),
                status=HTTPStatus.NOT_FOUND.value,
                stack_trace=traceback.format_exc(),
            )
        response = handler(chat=self.chat_helper.chat, data=self.data, plugins=self.plugins, user=self.user)
        response = {
            SmarterJournalApiResponseKeys.DATA: response,
        }
        response = SmarterJournaledJsonResponse(
            request=request,
            data=response,
            command=SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT),
            thing=SmarterJournalThings(SmarterJournalThings.CHATBOT),
            status=HTTPStatus.OK.value,
            safe=False,
        )
        self.helper_logger(f"{self.formatted_class_name} response={response}")
        return response
