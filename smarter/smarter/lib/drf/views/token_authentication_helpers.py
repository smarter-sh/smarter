"""Django template and view helper functions for knox token authentication."""

import logging
from http import HTTPStatus

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.utils.decorators import method_decorator
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.views import APIView

from smarter.apps.api.signals import api_request_completed, api_request_initiated
from smarter.common.conf import settings as smarter_settings
from smarter.common.utils import is_authenticated_request, smarter_build_absolute_uri
from smarter.lib.django import waffle
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.view_helpers import SmarterAuthenticatedPermissionClass
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from ..token_authentication import SmarterTokenAuthentication


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


# ------------------------------------------------------------------------------
# API Authenticated Views
# ------------------------------------------------------------------------------


@method_decorator(login_required, name="dispatch")
class SmarterAuthenticatedAPIView(APIView, SmarterRequestMixin):
    """Smarter base class for DRF API detail views that require authentication.

    Does the following:

    - Adds SmarterRequestMixin to the view, so that base Smarter functionality is available to all subclasses.
    - Adds SmarterTokenAuthentication to the default SessionAuthentication for authentication.
    - Overrides Django's logic for initializing the request object to ensure that SmarterRequestMixin is fully initialized before any other logic runs.
    """

    permission_classes = [SmarterAuthenticatedPermissionClass]
    authentication_classes = [SmarterTokenAuthentication, SessionAuthentication]

    def initial(self, request, *args, **kwargs):
        """Extend initial() DRF view method. Initialize the view with the request and any additional arguments.

        This is the earliest point in the DRF view lifecycle where the request object is available.
        Up to this point our SmarterRequestMixin, and AccountMixin classes are only partially
        initialized. This method takes care of the rest of the initialization.


        Args:
            request (HttpRequest): The incoming HTTP request.
        """
        if not self.is_requestmixin_ready:
            logger.info(
                "%s.initial() - completing initialization of SmarterRequestMixin with request: %s",
                self.formatted_class_name,
                request.build_absolute_uri(),
            )
            self.smarter_request = request
        logger.info(
            "%s.initial() - request: %s, args: %s, kwargs: %s",
            self.formatted_class_name,
            self.request,
            args,
            kwargs,
        )
        super().initial(self.request, *args, **kwargs)

    def setup(self, request: Request, *args, **kwargs):
        """Extend setup() DRF view method. Setup the view. This is called by Django before dispatch() and is used to
        set up the view for the request.

        Args:
            request (HttpRequest): The incoming HTTP request.
        """
        # drf setup logic
        super().setup(self.request, *args, **kwargs)

        # go through our own request and account mixin setup logic
        SmarterRequestMixin.__init__(self, request=request, *args, **kwargs)

        # overwrite the request object with our smarter_request object
        if not self.smarter_request:
            logger.warning(
                "%s.setup() - smarter_request is None, overwriting with request: %s",
                self.formatted_class_name,
                smarter_build_absolute_uri(request),
            )
            self.smarter_request = request
        self.request = self.smarter_request
        api_request_initiated.send(sender=self.__class__, instance=self, request=self.request)
        logger.info(
            "%s.setup() - finished for request: %s, user: %s, self.user: %s is_authenticated: %s",
            self.formatted_class_name,
            smarter_build_absolute_uri(self.request),
            self.request.user.username if self.request.user else "Anonymous",  # type: ignore[assignment]
            self.user_profile,
            is_authenticated_request(self.request),
        )


@method_decorator(login_required, name="dispatch")
class SmarterAuthenticatedListAPIView(ListAPIView, SmarterRequestMixin):
    """Smarter base class for DRF API list views that require authentication.

    Does the following:

    - Adds SmarterRequestMixin to the view, so that base Smarter functionality is available to all subclasses.
    - Adds SmarterTokenAuthentication to the default SessionAuthentication for authentication.
    - Overrides Django's logic for initializing the request object to ensure that SmarterRequestMixin is fully initialized before any other logic runs.

    """

    permission_classes = [SmarterAuthenticatedPermissionClass]
    authentication_classes = [SmarterTokenAuthentication, SessionAuthentication]

    def initial(self, request, *args, **kwargs):
        """Extend DRF initial() to add SmarterRequestMixin

        Args:
            request (HttpRequest): The incoming HTTP request.
        """
        logger.info(
            "%s.initial() - request: %s, args: %s, kwargs: %s",
            self.formatted_class_name,
            request,
            args,
            kwargs,
        )
        SmarterRequestMixin.__init__(self, request, *args, **kwargs)
        super().initial(self.request, *args, **kwargs)


# ------------------------------------------------------------------------------
# Admin API Views
# ------------------------------------------------------------------------------
@method_decorator(staff_member_required, name="dispatch")
class SmarterAdminAPIView(APIView, SmarterRequestMixin):
    """Smarter base class for DRF API views that require admin authentication.

    Does the following:

    - Adds SmarterRequestMixin to the view, so that base Smarter functionality is available to all subclasses.
    - Adds SmarterTokenAuthentication to the default SessionAuthentication for authentication.
    - Overrides Django's logic for initializing the request object to ensure that
      SmarterRequestMixin is fully initialized before any other logic runs.
    - Limits access to admin users only (staff/superusers).
    """

    permission_classes = [SmarterAuthenticatedPermissionClass]
    authentication_classes = [SmarterTokenAuthentication, SessionAuthentication]

    def setup(self, request: Request, *args, **kwargs):
        """Extend DRF setup() the view. This is called by Django before dispatch() and is used to
        set up the view for the request.

        Args:
            request (Request): The incoming HTTP request.
        """
        logger.info(
            "%s.setup() - called for request: %s", self.formatted_class_name, smarter_build_absolute_uri(request)
        )

        # experiment: we want to ensure that the request object is
        # initialized before we call the SmarterRequestMixin.
        SmarterRequestMixin.__init__(self, request=request, *args, **kwargs)

        # note: setup() is the earliest point in the request lifecycle where we can
        # send signals.
        api_request_initiated.send(sender=self.__class__, instance=self, request=self.request)
        logger.info(
            "CliBaseApiView().setup() - request: %s, user: %s, self.user: %s is_authenticated: %s",
            smarter_build_absolute_uri(self.request),
            self.request.user.username if self.request.user else "Anonymous",  # type: ignore[assignment]
            self.user_profile,
            is_authenticated_request(self.request),
        )
        super().setup(self.request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        """Extend DRF dispatch() to add authentication check.

        Args:
            request (HttpRequest): The incoming HTTP request.

        Raises:
            AuthenticationFailed: Raised when authentication fails.
            SmarterTokenAuthenticationError: Raised for errors specific to SmarterTokenAuthentication.
        """
        if not is_authenticated_request(request):
            logger.warning(
                "%s.dispatch() - request user is not authenticated: %s",
                self.formatted_class_name,
                request.user,
            )
            return HttpResponseForbidden("Forbidden: Invalid or missing authentication credentials.")

        try:
            response = super().dispatch(request, *args, **kwargs)
        # pylint: disable=broad-except
        except AttributeError:
            # catches an error raised by a decorator elsewhere in the stack that
            # barfs when the user object is None
            # File "/home/smarter_user/venv/lib/python3.12/site-packages/django/contrib/admin/views/decorators.py", line 13, in <lambda>
            return HttpResponseForbidden("Forbidden: Invalid or missing authentication credentials.")
        logger.info(
            "%s.dispatch() - request: %s, user: %s",
            self.formatted_class_name,
            smarter_build_absolute_uri(self.request),
            self.request.user.username if self.request.user else "Anonymous",  # type: ignore[assignment]
        )
        api_request_completed.send(sender=self.__class__, instance=self, request=self.request, response=response)
        return response

    def is_superuser_or_unauthorized(self):
        """Check if the authenticated user is a superuser.

        Returns:
            bool: True if the user is not a superuser, False otherwise.
        """
        if not self.user_profile or not self.user_profile.user.is_superuser:
            return JsonResponse({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
        return False


@method_decorator(staff_member_required, name="dispatch")
class SmarterAdminListAPIView(ListAPIView, SmarterRequestMixin):
    """Smarter base class for DRF list views that require admin access.

    Does the following:

    - Adds SmarterRequestMixin to the view, so that base Smarter functionality is available to all subclasses.
    - Adds SmarterTokenAuthentication to the default SessionAuthentication for authentication.
    - Overrides Django's logic for initializing the request object to ensure that
      SmarterRequestMixin is fully initialized before any other logic runs.
    - Limits access to admin users only (staff/superusers).
    """

    permission_classes = [SmarterAuthenticatedPermissionClass]
    authentication_classes = [SmarterTokenAuthentication, SessionAuthentication]

    def setup(self, request: Request, *args, **kwargs):
        """Extend DRF setup() to add Django signals.

        Args:
            request (Request): The incoming HTTP request.
        """
        super().setup(request, *args, **kwargs)
        SmarterRequestMixin.__init__(self, request=request, *args, **kwargs)

        # note: setup() is the earliest point in the request lifecycle where we can
        # send signals.
        api_request_initiated.send(sender=self.__class__, instance=self, request=request)
        logger.info(
            "%s.setup() - request: %s, user: %s, user_profile: %s is_authenticated: %s",
            self.formatted_class_name,
            smarter_build_absolute_uri(self.request),
            self.request.user.username if self.request.user else "Anonymous",  # type: ignore[assignment]
            self.user_profile,
            is_authenticated_request(self.request),
        )

    def initial(self, request, *args, **kwargs):
        """Extend DRF initial() to add app logging.

        Args:
            request (HttpRequest): The incoming HTTP request.
        """
        super().initial(request, *args, **kwargs)
        logger.info(
            "%s.initial() - running for request: %s, user: %s, args: %s, kwargs: %s",
            self.formatted_class_name,
            request,
            request.user.username if request.user else "Anonymous",  # type: ignore[assignment]
            args,
            kwargs,
        )

    def dispatch(self, request, *args, **kwargs):
        """Extend DRF dispatch() to add authentication checks and logging.

        Args:
            request (HttpRequest): The incoming HTTP request.

        Returns:
            HttpResponse: The HTTP response generated by the view.

        Raises:
            AuthenticationFailed: Raised when authentication fails.
            SmarterTokenAuthenticationError: Raised for errors specific to SmarterTokenAuthentication.
        """
        if not is_authenticated_request(request):
            logger.warning(
                "%s.dispatch() - request user is not authenticated: %s",
                self.formatted_class_name,
                request.user,
            )
            return HttpResponseForbidden("Forbidden: Invalid or missing authentication credentials.")

        try:
            response = super().dispatch(request, *args, **kwargs)
        except AttributeError:
            # catches an error raised by a decorator elsewhere in the stack that
            # barfs when the user object is None
            # File "/home/smarter_user/venv/lib/python3.12/site-packages/django/contrib/admin/views/decorators.py", line 13, in <lambda>
            return HttpResponseForbidden("Forbidden: Invalid or missing authentication credentials.")

        logger.info(
            "%s.dispatch() - request: %s, user: %s",
            self.formatted_class_name,
            smarter_build_absolute_uri(self.request),
            self.request.user.username if self.request.user else "Anonymous",  # type: ignore[assignment]
        )
        return response

    def finalize_response(self, request, response, *args, **kwargs):
        """Extend DRF finalize_response() to add logging and signals.

        Args:
            request (HttpRequest): The incoming HTTP request.
            response (HttpResponse): The outgoing HTTP response.
        """
        logger.info(
            "%s.finalize_response() called for %s", self.formatted_class_name, smarter_build_absolute_uri(request)
        )
        api_request_completed.send(sender=self.__class__, instance=self, request=request, response=response)
        return super().finalize_response(request, response, *args, **kwargs)
