# pylint: disable=W0611
"""Orchestrator api/v1/orchestrators base view, for invoking a Orchestrator."""

from http import HTTPStatus
from typing import Optional

from django.core.handlers.asgi import ASGIRequest
from django.http import HttpResponseNotAllowed, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response

from smarter.apps.account.models.budget import charge_authorization
from smarter.apps.orchestrator.exceptions import SmarterOrchestratorException
from smarter.apps.orchestrator.models import (
    Orchestrator,
)
from smarter.apps.orchestrator.serializers import OrchestratorSerializer
from smarter.apps.orchestrator.signals import orchestrator_called
from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterHttpMethods
from smarter.lib import logging
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

base_logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ORCHESTRATOR])
logger = base_logger


# pylint: disable=too-many-instance-attributes
@method_decorator(csrf_exempt, name="dispatch")
class OrchestratorApiBaseViewSet(SmarterAuthenticatedNeverCachedWebView):
    """
    Base viewset for all Orchestrator API endpoints.

    This class serves as the foundational viewset for all orchestrator-related APIs in the Smarter platform,
    including prompt completions that leverage the Smarter LLM Tool Call Plugin architecture.

    **Key Responsibilities:**

    - **API Key Authentication and Request Validation:**
      Enforces authentication for all API requests, rejecting those without a valid API key.

    - **Lifecycle Management:**
      Handles initialization of Account, Orchestrator, OrchestratorHelper, and PromptHelper objects, and manages request dispatching
      and routing to the appropriate handler methods.

    - **Logging and Observability:**
      Provides robust logging and observability for all major lifecycle events, including error handling.

    **Django Integration:**

    - Subclasses Django's view-template system (not DRF), participating in the standard request/response lifecycle.
    - Overrides and extends methods such as ``setup()``, ``dispatch()``, ``get()``, and ``post()`` to provide orchestrator-specific logic.
    - CSRF-exempt to support API clients.

    **Prompt Completion & LLM Tool Call Plugins:**

    - This base view is designed to support prompt completion endpoints that utilize Smarter's LLM Tool Call Plugin architecture.
    - Plugins can be discovered and invoked as part of the orchestrator's response generation, enabling extensible and dynamic tool use.

    **Examples:**

    **Notes:**

    - Intended to be subclassed by concrete orchestrator API views.
    - Provides robust error handling and logging for all major operations.
    - Authentication is enforced by default.
    - CSRF-exempt for API compatibility.

    **See Also:**
        - Django REST Framework View lifecycle: https://www.django-rest-framework.org/api-guide/views/#view-initialization
        - SmarterRequestMixin for request context management.
        - OrchestratorHelper and PromptHelper for orchestrator and prompt session logic.
        - Smarter LLM Tool Call Plugin architecture documentation.
    """

    _orchestrator_id: Optional[int] = None
    _orchestrator: Orchestrator
    _name: Optional[str] = None

    http_method_names: list[str] = ["get", "post", "options"]

    @property
    def orchestrator_id(self):
        """
        Returns the orchestrator ID.

        :return: The orchestrator ID.
        :rtype: Optional[int]
        """
        return self.orchestrator.id if self.orchestrator else self._orchestrator_id  # type: ignore

    @property
    def name(self):
        """
        Returns the name of the orchestrator.

        :return: The name of the orchestrator.
        :rtype: Optional[str]
        """
        if self._name:
            return self._name
        self._name = self.orchestrator.name if self.orchestrator else None

    @property
    def orchestrator(self):
        """
        Returns the Orchestrator instance.

        :return: The Orchestrator instance.
        :rtype: Optional[Orchestrator]
        """
        return self._orchestrator

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the class name in a formatted string.

        along with the name of this mixin.

        :return: Formatted class name string.
        :rtype: str
        """
        class_name = f"{__name__}.{OrchestratorApiBaseViewSet.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def setup(self, request: ASGIRequest, *args, **kwargs):
        """
        Set up the Orchestrator API base viewset for request processing.

        This method is called as part of the Django REST Framework (DRF) view lifecycle,
        immediately after the view instance is created and before the request is dispatched
        to the appropriate handler method (such as ``get()`` or ``post()``).

        The primary responsibilities of this method are to:

        - Initialize the :class:`SmarterRequestMixin` with the current request and any additional arguments.
        - Prepare and set up the :class:`OrchestratorHelper` and :class:`PromptHelper` instances, which are used
          throughout the request lifecycle for orchestrator-specific logic and prompt session management.
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
        - OrchestratorHelper and PromptHelper for orchestrator and prompt session logic.
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
        Dispatch method for the Orchestrator API base viewset.

        This method is invoked as part of the Django REST Framework (DRF) view lifecycle.
        It is responsible for preparing the viewset for request processing, including
        initializing the OrchestratorHelper and PromptHelper instances, setting up the request context,
        and logging relevant information for observability and debugging.

        The dispatch method performs the following key actions:

        - Extracts and sets the orchestrator ID from the URL parameters, if present.
        - Initializes the Orchestrator and Account context for the request.
        - Validates the existence and readiness of the OrchestratorHelper and Orchestrator instances.
        - Handles error conditions such as missing or invalid orchestrator configuration, returning
          appropriate HTTP error responses.
        - Loads and attaches plugins for the orchestrator, if available.
        - Emits signals and logs key request metadata for auditing and debugging.
        - Calls the parent class's dispatch method to continue the DRF request/response lifecycle.

        Parameters
        ----------
        request : ASGIRequest
            The HTTP request object provided by Django, containing all request data, headers, and user context.

        *args
            Additional positional arguments passed to the view.

        name : Optional[str]
            The name of the orchestrator, if provided as a URL parameter.

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
        - OrchestratorHelper and PromptHelper for orchestrator and prompt session logic.
        """
        self._orchestrator_id = kwargs.get("orchestrator_id")
        if self._orchestrator_id:
            kwargs.pop("orchestrator_id")
        else:
            self._name = self._name or name
        if not self.orchestrator:
            logger.warning(
                "Could not initialize Orchestrator url: %s, name: %s, user: %s, account: %s, id: %s",
                self.url,
                self.name,
                self.user,
                self.account,
                self.orchestrator_id,
            )
            return JsonResponse({}, status=HTTPStatus.NOT_FOUND.value)

        if not self.orchestrator:
            raise SmarterOrchestratorException(
                f"OrchestratorHelper not found. request={self.smarter_request} name={self.name}, orchestrator_id={self.orchestrator_id}, session_key={self.session_key}, user_profile={self.user_profile}"
            )
        if not self.orchestrator.ready:
            data = {
                "data": {
                    "error": {
                        "message": "Could not initialize Orchestrator object.",
                        "account": self.account.account_number if self.account else None,
                        "orchestrator": OrchestratorSerializer(self.orchestrator).data if self.orchestrator else None,
                        "user": self.user.username if self.user else None,
                        "name": self.orchestrator.name,
                    },
                },
            }
            logger.debug("%s.dispatch() - Orchestrator not ready", self.formatted_class_name)
            return JsonResponse(data=data, status=HTTPStatus.BAD_REQUEST.value)

        if self.orchestrator:
            charge_authorization(self.orchestrator.record_locator, self.__class__.__name__)  # type: ignore
            orchestrator_called.send(
                sender=self.__class__,
                orchestrator=self.orchestrator,
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
        logger.debug("%s.options(): orchestrator=%s", self.formatted_class_name, self.orchestrator)
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
