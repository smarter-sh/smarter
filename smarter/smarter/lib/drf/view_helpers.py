"""Django template and view helper functions."""

import logging

from knox.auth import TokenAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from rest_framework.generics import ListAPIView
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.views import APIView

from smarter.apps.account.models import SmarterAuthToken


logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# API public views
# ------------------------------------------------------------------------------
class UnauthenticatedPermissionClass(BasePermission):
    """
    Allows public access to APIS.
    """

    def has_permission(self, request, view):
        return True


class SmarterUnauthenticatedAPIView(APIView):
    """Base API view for smarter."""

    permission_classes = [UnauthenticatedPermissionClass]
    http_method_names = ["get"]


class SmarterUnauthenticatedAPIListView(ListAPIView):
    """Base API listview for smarter."""

    permission_classes = [UnauthenticatedPermissionClass]
    http_method_names = ["get"]


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


class SmarterAuthenticatedAPIView(APIView):
    """
    Allows access only to authenticated users.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [SmarterTokenAuthentication, SessionAuthentication]

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_anonymous:
            raise NotAuthenticated()
        return super().dispatch(request, *args, **kwargs)


class SmarterAuthenticatedListAPIView(ListAPIView):
    """
    Allows access only to authenticated users.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [SmarterTokenAuthentication, SessionAuthentication]

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_anonymous:
            raise NotAuthenticated()
        return super().dispatch(request, *args, **kwargs)


# ------------------------------------------------------------------------------
# Admin API Views
# ------------------------------------------------------------------------------
class AdminPermissionsClass(IsAuthenticated):
    """
    Custom permission to only allow access to staff users.
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.is_staff or request.user.is_superuser


class SmarterAdminAPIView(APIView):
    """
    Allows access only to admins.
    """

    permission_classes = [AdminPermissionsClass]
    authentication_classes = [SessionAuthentication]

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_anonymous:
            raise NotAuthenticated()
        return super().dispatch(request, *args, **kwargs)


class SmarterAdminListAPIView(ListAPIView):
    """
    Allows access only to admins.
    """

    permission_classes = [AdminPermissionsClass]
    authentication_classes = [SessionAuthentication]

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_anonymous:
            raise NotAuthenticated()
        return super().dispatch(request, *args, **kwargs)
