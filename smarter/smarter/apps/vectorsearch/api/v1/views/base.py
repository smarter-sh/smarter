# pylint: disable=W0611
"""Vectorsearch api/v1/vectorsearchs base view, for invoking a Vectorsearch."""

from http import HTTPStatus
from typing import Optional

from django.core.handlers.asgi import ASGIRequest
from django.http import HttpResponseNotAllowed, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response

from smarter.apps.account.models.budget import charge_authorization
from smarter.apps.vectorsearch.exceptions import SmarterVectorsearchException
from smarter.apps.vectorsearch.models import (
    Vectorsearch,
)
from smarter.apps.vectorsearch.serializers import VectorsearchSerializer
from smarter.apps.vectorsearch.signals import vectorsearch_called
from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterHttpMethods
from smarter.lib import logging
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

base_logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.VECTORSEARCH_LOGGING])
logger = base_logger


# pylint: disable=too-many-instance-attributes
@method_decorator(csrf_exempt, name="dispatch")
class VectorsearchApiBaseViewSet(SmarterAuthenticatedNeverCachedWebView):
    """
    Base viewset for all Vectorsearch API endpoints.

    This class serves as the foundational viewset for all vectorsearch-related APIs in the Smarter platform,
    including prompt completions that leverage the Smarter LLM Tool Call Plugin architecture.

    **Key Responsibilities:**

    - **API Key Authentication and Request Validation:**
      Enforces authentication for all API requests, rejecting those without a valid API key.

    - **Lifecycle Management:**
      Handles initialization of Account, Vectorsearch, VectorsearchHelper, and PromptHelper objects, and manages request dispatching
      and routing to the appropriate handler methods.

    - **Logging and Observability:**
      Provides robust logging and observability for all major lifecycle events, including error handling.

    **Django Integration:**

    - Subclasses Django's view-template system (not DRF), participating in the standard request/response lifecycle.
    - Overrides and extends methods such as ``setup()``, ``dispatch()``, ``get()``, and ``post()`` to provide vectorsearch-specific logic.
    - CSRF-exempt to support API clients.

    **Prompt Completion & LLM Tool Call Plugins:**

    - This base view is designed to support prompt completion endpoints that utilize Smarter's LLM Tool Call Plugin architecture.
    - Plugins can be discovered and invoked as part of the vectorsearch's response generation, enabling extensible and dynamic tool use.

    **Examples:**

    **Notes:**

    - Intended to be subclassed by concrete vectorsearch API views.
    - Provides robust error handling and logging for all major operations.
    - Authentication is enforced by default.
    - CSRF-exempt for API compatibility.

    **See Also:**
        - Django REST Framework View lifecycle: https://www.django-rest-framework.org/api-guide/views/#view-initialization
        - SmarterRequestMixin for request context management.
        - VectorsearchHelper and PromptHelper for vectorsearch and prompt session logic.
        - Smarter LLM Tool Call Plugin architecture documentation.
    """

    _vectorsearch_id: Optional[int] = None
    _vectorsearch: Vectorsearch
    _name: Optional[str] = None

    http_method_names: list[str] = ["get", "post", "options"]

    @property
    def vectorsearch_id(self):
        """
        Returns the vectorsearch ID.

        :return: The vectorsearch ID.
        :rtype: Optional[int]
        """
        return self.vectorsearch.id if self.vectorsearch else self._vectorsearch_id  # type: ignore

    @property
    def name(self):
        """
        Returns the name of the vectorsearch.

        :return: The name of the vectorsearch.
        :rtype: Optional[str]
        """
        if self._name:
            return self._name
        self._name = self.vectorsearch.name if self.vectorsearch else None

    @property
    def vectorsearch(self):
        """
        Returns the Vectorsearch instance.

        :return: The Vectorsearch instance.
        :rtype: Optional[Vectorsearch]
        """
        return self._vectorsearch

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the class name in a formatted string.

        along with the name of this mixin.

        :return: Formatted class name string.
        :rtype: str
        """
        class_name = f"{__name__}.{VectorsearchApiBaseViewSet.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def setup(self, request: ASGIRequest, *args, **kwargs):
        """
        Set up the Vectorsearch API base viewset for request processing.

        This method is called as part of the Django REST Framework (DRF) view lifecycle,
        immediately after the view instance is created and before the request is dispatched
        to the appropriate handler method (such as ``get()`` or ``post()``).

        The primary responsibilities of this method are to:

        - Initialize the :class:`SmarterRequestMixin` with the current request and any additional arguments.
        - Prepare and set up the :class:`VectorsearchHelper` and :class:`PromptHelper` instances, which are used
          throughout the request lifecycle for vectorsearch-specific logic and prompt session management.
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
        - VectorsearchHelper and PromptHelper for vectorsearch and prompt session logic.
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
        Dispatch method for the Vectorsearch API base viewset.

        This method is invoked as part of the Django REST Framework (DRF) view lifecycle.
        It is responsible for preparing the viewset for request processing, including
        initializing the VectorsearchHelper and PromptHelper instances, setting up the request context,
        and logging relevant information for observability and debugging.

        The dispatch method performs the following key actions:

        - Extracts and sets the vectorsearch ID from the URL parameters, if present.
        - Initializes the Vectorsearch and Account context for the request.
        - Validates the existence and readiness of the VectorsearchHelper and Vectorsearch instances.
        - Handles error conditions such as missing or invalid vectorsearch configuration, returning
          appropriate HTTP error responses.
        - Loads and attaches plugins for the vectorsearch, if available.
        - Emits signals and logs key request metadata for auditing and debugging.
        - Calls the parent class's dispatch method to continue the DRF request/response lifecycle.

        Parameters
        ----------
        request : ASGIRequest
            The HTTP request object provided by Django, containing all request data, headers, and user context.

        *args
            Additional positional arguments passed to the view.

        name : Optional[str]
            The name of the vectorsearch, if provided as a URL parameter.

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
        - VectorsearchHelper and PromptHelper for vectorsearch and prompt session logic.
        """
        self._vectorsearch_id = kwargs.get("vectorsearch_id")
        if self._vectorsearch_id:
            kwargs.pop("vectorsearch_id")
        else:
            self._name = self._name or name
        if not self.vectorsearch:
            logger.warning(
                "Could not initialize Vectorsearch url: %s, name: %s, user: %s, account: %s, id: %s",
                self.url,
                self.name,
                self.user,
                self.account,
                self.vectorsearch_id,
            )
            return JsonResponse({}, status=HTTPStatus.NOT_FOUND.value)

        if not self.vectorsearch:
            raise SmarterVectorsearchException(
                f"VectorsearchHelper not found. request={self.smarter_request} name={self.name}, vectorsearch_id={self.vectorsearch_id}, session_key={self.session_key}, user_profile={self.user_profile}"
            )
        if not self.vectorsearch.ready:
            data = {
                "data": {
                    "error": {
                        "message": "Could not initialize Vectorsearch object.",
                        "account": self.account.account_number if self.account else None,
                        "vectorsearch": VectorsearchSerializer(self.vectorsearch).data if self.vectorsearch else None,
                        "user": self.user.username if self.user else None,
                        "name": self.vectorsearch.name,
                    },
                },
            }
            logger.debug("%s.dispatch() - Vectorsearch not ready", self.formatted_class_name)
            return JsonResponse(data=data, status=HTTPStatus.BAD_REQUEST.value)

        if self.vectorsearch:
            charge_authorization(self.vectorsearch.record_locator, self.__class__.__name__)  # type: ignore
            vectorsearch_called.send(
                sender=self.__class__,
                vectorsearch=self.vectorsearch,
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
        logger.debug("%s.options(): vectorsearch=%s", self.formatted_class_name, self.vectorsearch)
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
