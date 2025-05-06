# pylint: disable=W0707,W0718,W0613
"""Views for unit tests."""
import logging

from rest_framework import status
from rest_framework.response import Response

from smarter.lib.drf.view_helpers import (
    SmarterUnauthenticatedAPIListView,
    SmarterUnauthenticatedAPIView,
)
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
    SmarterAuthenticatedListAPIView,
)


logger = logging.getLogger(__name__)
faux_dict = {
    "message": "This is a test JSON response. This data is static, and it is not real.",
    "status": "success",
    "data": {"id": 1, "name": "Test User", "email": "testuser@example.com"},
}
faux_list = [
    {
        "id": i,
        **faux_dict,
        "message": f"This is a test JSON response for item {i}. This data is static, and it is not real.",
    }
    for i in range(1, 6)
]


class TestJsonDictView(SmarterUnauthenticatedAPIView):
    """Returns a JSON dict for testing purposes."""

    def get(self, request, *args, **kwargs):
        """Handle GET requests and return a faux JSON dictionary."""
        return Response(faux_dict, status=status.HTTP_200_OK)


class TestJsonListView(SmarterUnauthenticatedAPIListView):
    """Returns a list of JSON dicts for testing purposes."""

    def get_queryset(self):
        """Provide a faux queryset for the view."""
        return faux_list

    def get(self, request, *args, **kwargs):
        """Handle GET requests and return a faux JSON list."""
        queryset = self.get_queryset()  # Use the faux queryset
        return Response(queryset, status=status.HTTP_200_OK)


class TestJsonDictViewAuthenticated(SmarterAuthenticatedAPIView):
    """Returns a JSON dict for testing purposes."""

    def get(self, request, *args, **kwargs):
        """Handle GET requests and return a faux JSON dictionary."""
        return Response(faux_dict, status=status.HTTP_200_OK)


class TestJsonListViewAuthenticated(SmarterAuthenticatedListAPIView):
    """Returns a list of JSON dicts for testing purposes."""

    def get_queryset(self):
        """Provide a faux queryset for the view."""
        return faux_list

    def get(self, request, *args, **kwargs):
        """Handle GET requests and return a faux JSON list."""
        queryset = self.get_queryset()  # Use the faux queryset
        return Response(queryset, status=status.HTTP_200_OK)
