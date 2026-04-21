# pylint: disable=W0707,W0718
"""Account views for smarter api."""

import logging
from http import HTTPStatus
from typing import Optional

from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.account.models import Account, UserProfile
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .base import AccountViewBase


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class BatchCreateUsersView(AccountViewBase):
    """Account view for smarter api."""

    def get(self, request: Request, account_id: int):
        return HttpResponseBadRequest(
            "GET method is not allowed for this endpoint. Please use POST to batch create users."
        )

    def patch(self, request: Request, account_id: Optional[int] = None):
        return HttpResponseBadRequest(
            "PATCH method is not allowed for this endpoint. Please use POST to batch create users."
        )

    def delete(self, request, account_id: int):
        return HttpResponseBadRequest(
            "DELETE method is not allowed for this endpoint. Please use POST to batch create users."
        )

    def post(self, request: Request):
        """
        Handle batch user creation. Receives a list of user data in the
        request body and creates users for the specified account.

        Expected request body format:
        {
            "account_id": 123,
            "users": [
                {
                    "username": "user1",
                    "email": "user1@example.com",
                    "first_name": "User",
                    "last_name": "One",
                },
                {
                    "username": "user2",
                    "email": "user2@example.com",
                    "first_name": "User",
                    "last_name": "Two",
                }
            ]
        }

        Returns a JSON response with the results of the batch user creation.
        Response format:

        {
            "created_users": [
                {
                    "username": "user1",
                    "email": "user1@example.com",
                    "first_name": "User",
                    "last_name": "One",
                    "status": "success",
                },
                {
                    "username": "user2",
                    "email": "user2@example.com",
                    "first_name": "User",
                    "last_name": "Two",
                    "status": "failure",
                    "error": "Error message describing the failure",
                }
            ]
        }
        """
        return HttpResponse(
            "Batch user creation is not yet implemented. This endpoint is a placeholder for future implementation.",
            status=HTTPStatus.NOT_IMPLEMENTED,
        )
