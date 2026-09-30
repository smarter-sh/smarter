# pylint: disable=W0611
"""LLMHost api/v1/llmhosts base view, for invoking a LLMHost."""

from http import HTTPStatus
from typing import Optional

from django.core.handlers.asgi import ASGIRequest
from django.http import HttpResponseNotAllowed, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response

from smarter.apps.account.models.budget import charge_authorization
from smarter.apps.llmhost.exceptions import SmarterLLMHostException
from smarter.apps.llmhost.models import (
    LLMHost,
)
from smarter.apps.llmhost.serializers import LLMHostSerializer
from smarter.apps.llmhost.signals import llmhost_called
from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterHttpMethods
from smarter.lib import logging
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

base_logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_HOST_LOGGING])
logger = base_logger


# pylint: disable=too-many-instance-attributes
@method_decorator(csrf_exempt, name="dispatch")
class LLMHostApiBaseViewSet(SmarterAuthenticatedNeverCachedWebView):
    """
    Base viewset for all LLMHost API endpoints.

    This class serves as the foundational viewset for all llmhost-related APIs in the Smarter platform,
    including prompt completions that leverage the Smarter LLM Tool Call Plugin architecture.

    **Key Responsibilities:**

    - **API Key Authentication and Request Validation:**
      Enforces authentication for all API requests, rejecting those without a valid API key.

    - **Lifecycle Management:**
      Handles initialization of Account, LLMHost, LLMHostHelper, and PromptHelper objects, and manages request dispatching
      and routing to the appropriate handler methods.

    - **Logging and Observability:**
      Provides robust logging and observability for all major lifecycle events, including error handling.

    **Django Integration:**

    - Subclasses Django's view-template system (not DRF), participating in the standard request/response lifecycle.
    - Overrides and extends methods such as ``setup()``, ``dispatch()``, ``get()``, and ``post()`` to provide llmhost-specific logic.
    - CSRF-exempt to support API clients.

    **Prompt Completion & LLM Tool Call Plugins:**

    - This base view is designed to support prompt completion endpoints that utilize Smarter's LLM Tool Call Plugin architecture.
    - Plugins can be discovered and invoked as part of the llmhost's response generation, enabling extensible and dynamic tool use.

    **Examples:**

    **Notes:**

    - Intended to be subclassed by concrete llmhost API views.
    - Provides robust error handling and logging for all major operations.
    - Authentication is enforced by default.
    - CSRF-exempt for API compatibility.

    **See Also:**
        - Django REST Framework View lifecycle: https://www.django-rest-framework.org/api-guide/views/#view-initialization
        - SmarterRequestMixin for request context management.
        - LLMHostHelper and PromptHelper for llmhost and prompt session logic.
        - Smarter LLM Tool Call Plugin architecture documentation.
    """

    _llmhost_id: Optional[int] = None
    _llmhost: LLMHost
    _name: Optional[str] = None

    http_method_names: list[str] = ["get", "post", "options"]

    @property
    def llmhost_id(self):
        """
        Returns the llmhost ID.

        :return: The llmhost ID.
        :rtype: Optional[int]
        """
        return self.llmhost.id if self.llmhost else self._llmhost_id  # type: ignore

    @property
    def name(self):
        """
        Returns the name of the llmhost.

        :return: The name of the llmhost.
        :rtype: Optional[str]
        """
        if self._name:
            return self._name
        self._name = self.llmhost.name if self.llmhost else None

    @property
    def llmhost(self):
        """
        Returns the LLMHost instance.

        :return: The LLMHost instance.
        :rtype: Optional[LLMHost]
        """
        return self._llmhost

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the class name in a formatted string.

        along with the name of this mixin.

        :return: Formatted class name string.
        :rtype: str
        """
        class_name = f"{__name__}.{LLMHostApiBaseViewSet.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def setup(self, request: ASGIRequest, *args, **kwargs):
        """
        Set up the LLMHost API base viewset for request processing.

        This method is called as part of the Django REST Framework (DRF) view lifecycle,
        immediately after the view instance is created and before the request is dispatched
        to the appropriate handler method (such as ``get()`` or ``post()``).

        The primary responsibilities of this method are to:

        - Initialize the :class:`SmarterRequestMixin` with the current request and any additional arguments.
        - Prepare and set up the :class:`LLMHostHelper` and :class:`PromptHelper` instances, which are used
          throughout the request lifecycle for llmhost-specific logic and prompt session management.
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
        - LLMHostHelper and PromptHelper for llmhost and prompt session logic.
        """
        logger.debug(
            "%s.setup() - request: %s, args: %s, kwargs: %s",
            self.formatted_class_name,
            self.smarter_build_absolute_uri(request),
            args,
            kwargs,
        )
        super().setup(request, *args, **kwargs)

    def dispatch(self, request: ASGIRequest, *args, name: Optional[str] = None, **kwargs):
        """
        Dispatch method for the LLMHost API base viewset.

        This method is invoked as part of the Django REST Framework (DRF) view lifecycle.
        It is responsible for preparing the viewset for request processing, including
        initializing the LLMHostHelper and PromptHelper instances, setting up the request context,
        and logging relevant information for observability and debugging.

        The dispatch method performs the following key actions:

        - Extracts and sets the llmhost ID from the URL parameters, if present.
        - Initializes the LLMHost and Account context for the request.
        - Validates the existence and readiness of the LLMHostHelper and LLMHost instances.
        - Handles error conditions such as missing or invalid llmhost configuration, returning
          appropriate HTTP error responses.
        - Loads and attaches plugins for the llmhost, if available.
        - Emits signals and logs key request metadata for auditing and debugging.
        - Calls the parent class's dispatch method to continue the DRF request/response lifecycle.

        Parameters
        ----------
        request : ASGIRequest
            The HTTP request object provided by Django, containing all request data, headers, and user context.

        *args
            Additional positional arguments passed to the view.

        name : Optional[str]
            The name of the llmhost, if provided as a URL parameter.

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
        - LLMHostHelper and PromptHelper for llmhost and prompt session logic.
        """
        self._llmhost_id = kwargs.get("llmhost_id")
        if self._llmhost_id:
            kwargs.pop("llmhost_id")
        else:
            self._name = self._name or name
        if not self.llmhost:
            logger.warning(
                "Could not initialize LLMHost url: %s, name: %s, user: %s, account: %s, id: %s",
                self.url,
                self.name,
                self.user,
                self.account,
                self.llmhost_id,
            )
            return JsonResponse({}, status=HTTPStatus.NOT_FOUND.value)

        if not self.llmhost:
            raise SmarterLLMHostException(
                f"LLMHostHelper not found. request={self.smarter_request} name={self.name}, llmhost_id={self.llmhost_id}, session_key={self.session_key}, user_profile={self.user_profile}"
            )
        if not self.llmhost.ready:
            data = {
                "data": {
                    "error": {
                        "message": "Could not initialize LLMHost object.",
                        "account": self.account.account_number if self.account else None,
                        "llmhost": LLMHostSerializer(self.llmhost).data if self.llmhost else None,
                        "user": self.user.username if self.user else None,
                        "name": self.llmhost.name,
                    },
                },
            }
            logger.debug("%s.dispatch() - LLMHost not ready", self.formatted_class_name)
            return JsonResponse(data=data, status=HTTPStatus.BAD_REQUEST.value)

        if self.llmhost:
            charge_authorization(self.llmhost.record_locator, self.__class__.__name__)  # type: ignore
            llmhost_called.send(
                sender=self.__class__,
                llmhost=self.llmhost,
                request=request,
                data=self.data,
                args=args,
                kwargs=kwargs,
            )

        return super().dispatch(request, *args, **kwargs)

    def options(self, request, *args, **kwargs):
        """
        OPTIONS request handler for the Smarter Prompt API.

        Sets CORS headers to allow cross-origin requests from the Smarter environment URL.

        :param request: The HTTP request object.
        :type request: ASGIRequest
        """
        logger.debug("%s.options(): llmhost=%s", self.formatted_class_name, self.llmhost)
        response = Response()
        response["Access-Control-Allow-Origin"] = smarter_settings.environment_url
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "origin, content-type, accept"
        return response

    # pylint: disable=W0613
    def get(self, request, *args, name: Optional[str] = None, **kwargs):
        """
        GET request handler for the Smarter Prompt API.

        Currently, GET requests are not supported and will return a message indicating that POST should be used
        instead.

        :param request: The HTTP request object.
        :type request: ASGIRequest
        :return: A JsonResponse indicating that GET is not supported.
        :rtype: JsonResponse
        """

        return HttpResponseNotAllowed(permitted_methods=[SmarterHttpMethods.POST])
