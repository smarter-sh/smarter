"""DRF permission classes and base api views for Smarter's public and authenticated apis."""

from rest_framework.generics import ListAPIView
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView

from smarter.common.const import SMARTER_IS_INTERNAL_API_REQUEST
from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.common.utils import is_authenticated_request
from smarter.lib import logging

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# API public views
# ------------------------------------------------------------------------------
class UnauthenticatedPermissionClass(BasePermission):
    """Permission class that allows public access to apis."""

    # pylint: disable=unused-argument
    def has_all_permission(self, request: Request, view: APIView) -> bool:
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

    It is DRF's ``IsAuthenticated``, and adds a check that lets an authenticated internal api
    request through without a bearer token or other authentication method.
    """

    @property
    def formatted_class_name(self) -> str:
        """The permission class's dotted name, formatted for log messages."""
        class_name = f"{__name__}.{self.__class__.__name__}"
        return SmarterFormattedText.text(class_name)

    def has_all_permission(self, request: Request, view: APIView) -> bool:
        """
        Allow an authenticated request that is flagged as an internal api request.

        :param request: The request.
        :param view: The view.
        :returns: True only for an authenticated request flagged as an internal api request.
        """
        if is_authenticated_request(request) and getattr(request, SMARTER_IS_INTERNAL_API_REQUEST, False):
            logger.info(
                "%s.has_all_permission() - internal api request. Overriding permission: %s",
                self.formatted_class_name,
                request.build_absolute_uri(),
            )
            return True
        return False


class SmarterUnauthenticatedAPIView(APIView):
    """Base class of Smarter's public api views, which allow every request."""

    permission_classes = [UnauthenticatedPermissionClass]


class SmarterUnauthenticatedAPIListView(ListAPIView):
    """Base class of Smarter's public api list views, which allow every request."""

    permission_classes = [UnauthenticatedPermissionClass]
