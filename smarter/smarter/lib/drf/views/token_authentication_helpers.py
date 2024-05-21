"""Django template and view helper functions for knox token authentication."""

import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from ..token_authentication import SmarterTokenAuthentication


logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# API Authenticated Views
# ------------------------------------------------------------------------------


@method_decorator(login_required, name="dispatch")
class SmarterAuthenticatedAPIView(APIView):
    """
    Allows access only to authenticated users.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [SmarterTokenAuthentication, SessionAuthentication]


@method_decorator(login_required, name="dispatch")
class SmarterAuthenticatedListAPIView(ListAPIView):
    """
    Allows access only to authenticated users.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [SmarterTokenAuthentication, SessionAuthentication]


# ------------------------------------------------------------------------------
# Admin API Views
# ------------------------------------------------------------------------------
@method_decorator(staff_member_required, name="dispatch")
class SmarterAdminAPIView(APIView):
    """
    Allows access only to admins.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [SmarterTokenAuthentication, SessionAuthentication]


@method_decorator(staff_member_required, name="dispatch")
class SmarterAdminListAPIView(ListAPIView):
    """
    Allows access only to admins.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [SmarterTokenAuthentication, SessionAuthentication]
