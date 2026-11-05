"""DRF permission classes and base api views for Smarter's public and authenticated apis."""

from rest_framework.generics import ListAPIView
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView


# ------------------------------------------------------------------------------
# API public views
# ------------------------------------------------------------------------------
class UnauthenticatedPermissionClass(BasePermission):
    """Permission class that allows public access to apis."""

    # pylint: disable=unused-argument
    def has_permission(self, request: Request, view: APIView) -> bool:
        """
        Allow every request.

        :param request: The request.
        :param view: The view.
        :returns: Always True.
        """
        return True


class SmarterAuthenticatedPermissionClass(IsAuthenticated):
    """
    Permission class of api views that require an authenticated user.

    It is DRF's ``IsAuthenticated``: a request is allowed when its user is authenticated, however
    it was authenticated (an api key, a session, or an internal api request that carries its
    caller's user).
    """


class SmarterUnauthenticatedAPIView(APIView):
    """Base class of Smarter's public api views, which allow every request."""

    permission_classes = [UnauthenticatedPermissionClass]


class SmarterUnauthenticatedAPIListView(ListAPIView):
    """Base class of Smarter's public api list views, which allow every request."""

    permission_classes = [UnauthenticatedPermissionClass]
