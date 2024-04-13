"""Django template and view helper functions."""

from knox.auth import TokenAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import ListAPIView
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.views import APIView

from ..models import APIKey


class SmarterTokenAuthentication(TokenAuthentication):
    """
    Custom token authentication for smarter.
    This is used to authenticate API keys. It is a subclass of the default knox
    behavior, but it also checks that the API key is active.
    """

    model = APIKey

    def authenticate_credentials(self, token):
        # authenticate the user using the normal token authentication
        # this will raise an AuthenticationFailed exception if the token is invalid
        user, auth_token = super().authenticate_credentials(token)

        try:
            # next, we need to ensure that the token is active, otherwise
            # we should raise an exception that exactly matches the one
            # raised by the default token authentication
            APIKey.objects.get(token_key=auth_token.token_key, is_active=True)

            # if the token is active, we can return the user and token as a tuple
            # exactly as the default token authentication does.
            return (user, auth_token)
        except APIKey.DoesNotExist as e:
            raise AuthenticationFailed from e


# ------------------------------------------------------------------------------
# API Views
# ------------------------------------------------------------------------------
class IsStaffUser(BasePermission):
    """
    Custom permission to only allow access to staff users.
    """

    def has_permission(self, request, view):
        return request.user and (request.user.is_staff or request.user.is_superuser)


class SmarterAPIAuthenticated(IsAuthenticated):
    """
    Allows access only to authenticated users.
    """


class SmarterAPIAdmin(SmarterAPIAuthenticated, IsStaffUser):
    """
    Allows access only to admins.
    """


class SmarterAPIView(APIView):
    """Base API view for smarter."""

    permission_classes = [SmarterAPIAuthenticated]
    authentication_classes = [SmarterTokenAuthentication, SessionAuthentication]


class SmarterAPIListView(ListAPIView):
    """Base API listview for smarter."""

    permission_classes = [SmarterAPIAuthenticated]
    authentication_classes = [SmarterTokenAuthentication, SessionAuthentication]
    http_method_names = ["get"]


class SmarterAPIAdminView(SmarterAPIView):
    """Base admin-only API view."""

    permission_classes = [SmarterAPIAdmin]


class SmarterAPIListAdminView(SmarterAPIListView):
    """Base admin-only API list view."""

    permission_classes = [SmarterAPIAdmin]
