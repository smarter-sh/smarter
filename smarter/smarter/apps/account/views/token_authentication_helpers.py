"""Django template and view helper functions for knox token authentication."""

import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from knox.auth import TokenAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from ..models import SmarterAuthToken


logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# API Authenticated Views
# ------------------------------------------------------------------------------
class SmarterTokenAuthentication(TokenAuthentication):
    """
    Custom token authentication for smarter.
    This is used to authenticate API keys. It is a subclass of the default knox
    behavior, but it also checks that the API key is active.
    """

    model = SmarterAuthToken

    def authenticate_credentials(self, token):
        # authenticate the user using the normal token authentication
        # this will raise an AuthenticationFailed exception if the token is invalid
        user, auth_token = super().authenticate_credentials(token)

        # next, we need to ensure that the token is active, otherwise
        # we should raise an exception that exactly matches the one
        # raised by the default token authentication
        if not SmarterAuthToken.objects.filter(token_key=auth_token.token_key, is_active=True).exists():
            raise AuthenticationFailed

        # if the token is active, we can return the user and token as a tuple
        # exactly as the default token authentication does.
        return (user, auth_token)


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
