"""Django template and view helper functions for knox token authentication."""

import logging
from http import HTTPStatus

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView
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

    def initial(self, request, *args, **kwargs):
        """
        Initialize the view with the request and any additional arguments.
        """
        super().initial(request, *args, **kwargs)
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

    def initial(self, request, *args, **kwargs):
        """
        Initialize the view with the request and any additional arguments.
        """
        super().initial(request, *args, **kwargs)
        SmarterRequestMixin.__init__(self, request, *args, **kwargs)

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
        SmarterRequestMixin.__init__(self, request, *args, **kwargs)
