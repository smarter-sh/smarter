"""
The Stackademy course catalogue, ``/api/v1/demos/stackademy/course-catalogue/``.

Stackademy, https://github.com/smarter-sh/stackademy, is a fictional online code academy. Its course catalogue is the remote api that the
Stackademy ApiPlugin queries, so that the Stackademy LLMClients work on every platform
without an external service.
"""

import hmac
import os
from typing import Optional

from django.contrib.auth.models import AnonymousUser
from rest_framework import status
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.connection.models import ApiConnection
from smarter.common.exceptions import SmarterConfigurationError
from smarter.lib import json, logging
from smarter.lib.drf.views.helpers import SmarterUnauthenticatedAPIView
from smarter.lib.typing import SmarterDictType

from ..const import STACKADEMY_API_CONNECTION_NAME

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)

STACKADEMY_COURSES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stackademy_courses.json")


def stackademy_password() -> Optional[str]:
    """
    Return the password of the Stackademy course catalogue.

    It is the value of the ``apiKey`` Secret of the Smarter account's ApiConnection named
    :data:`STACKADEMY_API_CONNECTION_NAME`, which the Stackademy ApiPlugin uses.

    :returns: The Secret's value, or ``None`` if the connection or its ``apiKey`` does not exist.
    :rtype: Optional[str]
    """
    # not cached: a lookup before load_from_github creates the connection must not be remembered.
    connection = (
        ApiConnection.objects.filter(
            name=STACKADEMY_API_CONNECTION_NAME, user_profile__account=smarter_cached_objects.smarter_account
        )
        .select_related("api_key")
        .first()
    )
    if not connection or not connection.api_key:
        logger.error(
            "%s.stackademy_password() the Smarter account has no ApiConnection %s with an apiKey. "
            "Run manage.py load_from_github --url https://github.com/smarter-sh/stackademy --account_number %s.",
            logger_prefix,
            STACKADEMY_API_CONNECTION_NAME,
            smarter_cached_objects.smarter_account.account_number,
        )
        return None
    return connection.api_key.get_secret(update_last_accessed=False)


class StackademyBearerAuthentication(BaseAuthentication):
    """
    Authenticate a request whose bearer token is the Stackademy password.

    The request is anonymous: the token identifies no user, it only proves that the caller
    knows the password, e.g. ``Authorization: Bearer <password>``.
    """

    keyword = "Bearer"

    def authenticate(self, request):
        """
        Authenticate the request's bearer token.

        :param request: The request.
        :returns: ``(AnonymousUser, token)``, or ``None`` if the request has no bearer token.
        :raises AuthenticationFailed: If the token is malformed, or is not the password.
        """
        auth = get_authorization_header(request).split()
        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None
        if len(auth) != 2:
            raise AuthenticationFailed("Invalid bearer token header.")
        try:
            token = auth[1].decode()
        except UnicodeError as e:
            raise AuthenticationFailed("Invalid bearer token header.") from e
        password = stackademy_password()
        if not password or not hmac.compare_digest(token.encode(), password.encode()):
            raise AuthenticationFailed("Invalid bearer token.")
        return (AnonymousUser(), token)

    def authenticate_header(self, request) -> str:
        """The ``WWW-Authenticate`` header of a 401 response."""
        return f'{self.keyword} realm="api"'


class HasStackademyBearerToken(BasePermission):
    """Allow only the requests that :class:`StackademyBearerAuthentication` authenticated."""

    def has_permission(self, request, view) -> bool:
        return request.auth is not None


class StackademyCourseCatalogueView(SmarterUnauthenticatedAPIView):
    """
    The fictional Stackademy University's course catalogue.

    A ``GET`` returns the courses, filtered by the optional query parameters ``course_id``,
    ``max_cost`` and ``description``, a keyword that the course's description must contain.
    A request must send the Stackademy password as a bearer token, or it gets a 401.
    """

    authentication_classes = [StackademyBearerAuthentication]
    permission_classes = [HasStackademyBearerToken]

    def catalogue(self) -> list[SmarterDictType]:
        """
        Return every course in the catalogue.

        :returns: The courses.
        :rtype: list[SmarterDictType]
        :raises SmarterConfigurationError: If ``stackademy_courses.json`` is not valid JSON.
        """
        # the file is beside this module, not in the working directory.
        with open(STACKADEMY_COURSES, encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError as e:
                raise SmarterConfigurationError(
                    "Failed to decode JSON from stackademy_courses.json. "
                    "Please ensure the file is correctly formatted."
                ) from e

    def get(self, request: Request, *args, **kwargs):
        """Handle GET requests and return the filtered Stackademy course catalogue."""
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
