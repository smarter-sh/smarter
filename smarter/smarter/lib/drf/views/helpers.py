"""Django template and view helper functions."""

import logging

from rest_framework.generics import ListAPIView
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView

from smarter.common.const import SMARTER_IS_INTERNAL_API_REQUEST
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.utils import is_authenticated_request

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# API public views
# ------------------------------------------------------------------------------
class UnauthenticatedPermissionClass(BasePermission):
    """
    Allows public access to APIS.
    """

    def has_permission(self, request: Request, view) -> bool:
        return True


class SmarterAuthenticatedPermissionClass(IsAuthenticated):
    """
    Implements an internal API permission class that allows
    authenticated users to access internal API endpoints without
    requiring bearer tokens or other authentication methods.
    """

    @property
    def formatted_class_name(self) -> str:
        return formatted_text(f"{self.__class__.__module__}.{self.__class__.__name__}")

    def has_permission(self, request: Request, view) -> bool:
        """
        Allows internal view access to authenticated users and
        internal API requests.
        """
        if is_authenticated_request(request) and getattr(request, SMARTER_IS_INTERNAL_API_REQUEST, False):
            logger.info(
                "%s.has_permission() - internal api request. Overriding permission: %s",
                self.formatted_class_name,
                request.build_absolute_uri(),
            )
            return True
        return super().has_permission(request, view)


class SmarterUnauthenticatedAPIView(APIView):
    """Base API view for smarter."""

    permission_classes = [UnauthenticatedPermissionClass]


class SmarterUnauthenticatedAPIListView(ListAPIView):
    """Base API listview for smarter."""

    permission_classes = [UnauthenticatedPermissionClass]
