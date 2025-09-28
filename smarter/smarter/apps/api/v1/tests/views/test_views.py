# pylint: disable=W0707,W0718,W0613
"""Views for unit tests."""
import logging

from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.common.exceptions import SmarterConfigurationError
from smarter.lib import json
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


class FauxDictSerializer(serializers.Serializer):
    """Serializer for the faux dictionary used in test views."""

    id = serializers.IntegerField()
    message = serializers.CharField()
    status = serializers.CharField()
    data = serializers.DictField()  # type: ignore[call-arg]

    def create(self, validated_data):
        """Create a new instance of the serializer."""
        return validated_data

    def update(self, instance, validated_data):
        """Update an existing instance of the serializer."""
        instance.update(validated_data)
        return instance


class TestJsonDictView(SmarterUnauthenticatedAPIView):
    """Returns a JSON dict for testing purposes."""

    def get(self, request: Request, *args, **kwargs):
        """Handle GET requests and return a faux JSON dictionary."""
        return Response(faux_dict, status=status.HTTP_200_OK)


class TestJsonListView(SmarterUnauthenticatedAPIListView):
    """Returns a list of JSON dicts for testing purposes."""

    serializer_class = FauxDictSerializer

    def get_queryset(self):
        """Provide a faux queryset for the view."""
        return faux_list

    def get(self, request: Request, *args, **kwargs):
        """Handle GET requests and return a faux JSON list."""
        queryset = self.get_queryset()
        return Response(queryset, status=status.HTTP_200_OK)


class TestJsonDictViewAuthenticated(SmarterAuthenticatedAPIView):
    """Returns a JSON dict for testing purposes."""

    def get(self, request, *args, **kwargs):
        """Handle GET requests and return a faux JSON dictionary."""
        return Response(faux_dict, status=status.HTTP_200_OK)


class TestJsonListViewAuthenticated(SmarterAuthenticatedListAPIView):
    """Returns a list of JSON dicts for testing purposes."""

    serializer_class = FauxDictSerializer

    def get_queryset(self):
        """Provide a faux queryset for the view."""
        return faux_list

    def get(self, request, *args, **kwargs):
        """Handle GET requests and return a faux JSON list."""
        queryset = self.get_queryset()
        return Response(queryset, status=status.HTTP_200_OK)


class TestStackademyCourseCatalogueView(SmarterUnauthenticatedAPIView):
    """A placeholder view for the Stackademy course catalog."""

    def catalogue(self) -> list[dict]:

        with open("./stackaemy_courses.json", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError as e:
                raise SmarterConfigurationError(
                    "Failed to decode JSON from stackaemy_courses.json. "
                    "Please ensure the file is correctly formatted."
                ) from e
        return None

    def get(self, request: Request, *args, **kwargs):
        """
        Handle GET requests and return the faux Stackacademy
        course catalog.
        """
        course_id = request.query_params.get("course_id")
        max_cost = request.query_params.get("max_cost")
        description = request.query_params.get("description")

        filtered = self.catalogue()

        if course_id is not None:
            try:
                course_id = int(course_id)
                filtered = [c for c in filtered if c["course_id"] == course_id]
            except ValueError:
                pass

        if max_cost is not None:
            try:
                max_cost = float(max_cost)
                filtered = [c for c in filtered if c["cost"] <= max_cost]
            except ValueError:
                pass

        if description is not None:
            filtered = [c for c in filtered if description.lower() in c["description"].lower()]

        return Response(filtered, status=status.HTTP_200_OK)
