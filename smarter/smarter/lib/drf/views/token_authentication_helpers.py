"""Django template and view helper functions for knox token authentication."""

import logging
from http import HTTPStatus

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.views import APIView

from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.drf.view_helpers import SmarterAuthenticatedPermissionClass

from ..token_authentication import SmarterTokenAuthentication


logger = logging.getLogger(__name__)


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

    def __init__(self, *args, **kwargs):
        request = None
        SmarterRequestMixin.__init__(self, request, *args, **kwargs)
        super().__init__(*args, **kwargs)

    def initialize_request(self, request: HttpRequest, *args, **kwargs) -> Request:
        """
        This is the earliest point in the DRF view lifecycle where the request object is available.
        Up to this point our SmarterRequestMixin, and AccountMixin classes are only partially
        initialized. This method takes care of the rest of the initialization.
        """
        if not self.is_requestmixin_ready:
            logger.info(
                "%s.initialize_request() - completing initialization of SmarterRequestMixin with request: %s",
                self.formatted_class_name,
                request.build_absolute_uri(),
            )
            self.smarter_request = request
        return super().initialize_request(request, *args, **kwargs)

    def initial(self, request, *args, **kwargs):
        """
        Initialize the view with the request and any additional arguments.
        """
        super().initial(request, *args, **kwargs)
        logger.info(
            "%s.initial() - request: %s, args: %s, kwargs: %s",
            self.formatted_class_name,
            request,
            args,
            kwargs,
        )
        SmarterRequestMixin.__init__(self, request, *args, **kwargs)


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
        super().initial(request, *args, **kwargs)
        logger.info(
            "%s.initial() - request: %s, args: %s, kwargs: %s",
            self.formatted_class_name,
            request,
            args,
            kwargs,
        )
        SmarterRequestMixin.__init__(self, request, *args, **kwargs)


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

    def __init__(self, *args, **kwargs):
        request = None
        SmarterRequestMixin.__init__(self, request, *args, **kwargs)
        super().__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        """
        Initialize the view with the request and any additional arguments.
        """
        SmarterRequestMixin.__init__(self, request, *args, **kwargs)
        retval = super().dispatch(request, *args, **kwargs)
        logger.info(
            "%s.initial() - request: %s, args: %s, kwargs: %s",
            self.formatted_class_name,
            request,
            args,
            kwargs,
        )
        return retval

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

    def initial(self, request, *args, **kwargs):
        """
        Initialize the view with the request and any additional arguments.
        """
        super().initial(request, *args, **kwargs)
        logger.info(
            "%s.initial() - request: %s, args: %s, kwargs: %s",
            self.formatted_class_name,
            request,
            args,
            kwargs,
        )
        SmarterRequestMixin.__init__(self, request, *args, **kwargs)
