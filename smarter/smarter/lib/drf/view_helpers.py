"""Django template and view helper functions."""

import logging

from rest_framework.generics import ListAPIView
from rest_framework.permissions import BasePermission
from rest_framework.views import APIView


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


class SmarterUnauthenticatedAPIListView(ListAPIView):
    """Base API listview for smarter."""

    permission_classes = [UnauthenticatedPermissionClass]
