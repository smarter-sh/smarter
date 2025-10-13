"""Django template and view helper functions for knox token authentication."""

import logging
from http import HTTPStatus

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.views import APIView

from smarter.apps.api.signals import api_request_completed, api_request_initiated
from smarter.common.conf import settings as smarter_settings
from smarter.common.utils import smarter_build_absolute_uri
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
    """
    Allows access only to authenticated users.
    """

    permission_classes = [SmarterAuthenticatedPermissionClass]
    authentication_classes = [SmarterTokenAuthentication, SessionAuthentication]

    def initial(self, request, *args, **kwargs):
        """
        Initialize the view with the request and any additional arguments.

        This is the earliest point in the DRF view lifecycle where the request object is available.
        Up to this point our SmarterRequestMixin, and AccountMixin classes are only partially
        initialized. This method takes care of the rest of the initialization.
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
        """
        Setup the view. This is called by Django before dispatch() and is used to
        set up the view for the request.
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
            self.request.user.is_authenticated,
        )


@method_decorator(login_required, name="dispatch")
class SmarterAuthenticatedListAPIView(ListAPIView, SmarterRequestMixin):
    """
    Allows access only to authenticated users.
    """

    permission_classes = [SmarterAuthenticatedPermissionClass]
    authentication_classes = [SmarterTokenAuthentication, SessionAuthentication]

    def initial(self, request, *args, **kwargs):
        """
        Initialize the view with the request and any additional arguments.
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
    """
    Allows access only to admins.
    """

    permission_classes = [SmarterAuthenticatedPermissionClass]
    authentication_classes = [SmarterTokenAuthentication, SessionAuthentication]

    def setup(self, request: Request, *args, **kwargs):
        """
        Setup the view. This is called by Django before dispatch() and is used to
        set up the view for the request.
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
            self.request.user.is_authenticated,
        )
        super().setup(self.request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        logger.info(
            "%s.dispatch() - request: %s, user: %s",
            self.formatted_class_name,
            smarter_build_absolute_uri(self.request),
            self.request.user.username if self.request.user else "Anonymous",  # type: ignore[assignment]
        )
        api_request_completed.send(sender=self.__class__, instance=self, request=self.request, response=response)
        return response

    def is_superuser_or_unauthorized(self):
        """Check if the user is a superuser or unauthorized."""
        if not self.user_profile or not self.user_profile.user.is_superuser:
            return JsonResponse({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
        return False


@method_decorator(staff_member_required, name="dispatch")
class SmarterAdminListAPIView(ListAPIView, SmarterRequestMixin):
    """
    Allows access only to admins.
    """

    permission_classes = [SmarterAuthenticatedPermissionClass]
    authentication_classes = [SmarterTokenAuthentication, SessionAuthentication]

    def setup(self, request: Request, *args, **kwargs):
        """
        Setup the view. This is called by Django before dispatch() and is used to
        set up the view for the request.
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
            self.request.user.is_authenticated,
        )

    def initial(self, request, *args, **kwargs):
        """
        Initialize the view with the request and any additional arguments.
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
        response = super().dispatch(request, *args, **kwargs)
        logger.info(
            "%s.dispatch() - request: %s, user: %s",
            self.formatted_class_name,
            smarter_build_absolute_uri(self.request),
            self.request.user.username if self.request.user else "Anonymous",  # type: ignore[assignment]
        )
        api_request_completed.send(sender=self.__class__, instance=self, request=self.request, response=response)
        return response
