"""
Batch user creation view for smarter api.
"""

import logging
from typing import List, Optional

from django.core.management import call_command
from django.http import (
    HttpResponseBadRequest,
    JsonResponse,
)
from pydantic import BaseModel, EmailStr
from rest_framework.request import Request

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


class UserModel(BaseModel):
    """
    Pydantic model for user data in batch user creation.
    """

    username: str
    email: EmailStr
    first_name: str
    last_name: str
    password: Optional[str] = None
    is_admin: Optional[bool] = False


class BatchModel(BaseModel):
    """
    Pydantic model for batch user creation data.
    """

    account_number: str
    users: List[UserModel]


class CreatedUserModel(UserModel):
    """
    Pydantic model for created user data in batch user creation.
    """

    account_number: str
    status: str
    error: Optional[str] = None


class BatchCreateUsersResponseModel(BaseModel):
    """
    Pydantic model for the response of batch user creation.
    """

    created_users: List[CreatedUserModel]


class BatchCreateUsersView(AccountViewBase):
    """
    Batch user creation view for smarter api.

    path: /api/v1/accounts/batch-create-users/
    """

    def get(self, request: Request, *args, **kwargs):
        return HttpResponseBadRequest(
            "GET method is not allowed for this endpoint. Please use POST to batch create users."
        )

    def patch(self, request: Request, *args, **kwargs):
        return HttpResponseBadRequest(
            "PATCH method is not allowed for this endpoint. Please use POST to batch create users."
        )

    def delete(self, request: Request, *args, **kwargs):
        return HttpResponseBadRequest(
            "DELETE method is not allowed for this endpoint. Please use POST to batch create users."
        )

    def post(self, request: Request, *args, **kwargs):
        """
        Handle batch user creation. Receives a list of user data in the
        request body and creates users for the specified account. The process
        is as follows:

        1. Use Pydantic to validate the request body to ensure it contains the required fields.
        2. Iterate over the list of users and attempt to create each user using the Django management command `create_user`.
        3. Collect the results in a Pydantic model for each user creation attempt, including any errors that occur.
        4. Return a JSON model_dump() response summarizing the results of the batch user creation.

        Expected request body format:
            {
                "account_number": "1234-56789-0123",
                "users": [
                    {
                        "username": "user1",
                        "email": "user1@example.com",
                        "first_name": "User",
                        "last_name": "One",
                        "password": "optional_password",
                        "is_admin": false
                    },
                    ...
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
                        "is_staff": false,
                        "status": "success",
                    },
                    {
                        "username": "user2",
                        "email": "user2@example.com",
                        "first_name": "User",
                        "last_name": "Two",
                        "is_staff": false,
                        "status": "failure",
                        "error": "Error message describing the failure",
                    }
                ]
            }

        :param request: Django REST Framework request object containing batch user data.
        :type request: rest_framework.request.Request

        :returns: JsonResponse with the result of each attempted user creation.
        :rtype: django.http.JsonResponse

        :raises HttpResponseBadRequest: If the request body is missing or invalid.
        :raises Exception: If user creation fails for any user, the error is included in the response for that user.
        """
        logger.debug("Received batch user creation request: %s", request.data)
        if not request.data:
            return HttpResponseBadRequest("Request body is required.")
        data = request.data
        try:
            batch_data = BatchModel(**data)
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(f"Invalid request data: {e}")
            return HttpResponseBadRequest(f"Invalid request data: {e}")

        response = BatchCreateUsersResponseModel(created_users=[])
        account_number = batch_data.account_number
        i = 0
        for user in batch_data.users:
            i += 1
            logger.debug(
                f"Processing batch user creation for account number: {account_number} ({i}/{len(batch_data.users)}) users."
            )
            try:
                params: dict[str, str | bool] = {
                    "account_number": account_number,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                }
                if user.password:
                    params["password"] = user.password
                if user.is_admin:
                    params["admin"] = True

                call_command("create_user", **params)

                response.created_users.append(
                    CreatedUserModel(**user.model_dump(), account_number=account_number, status="success")
                )
            # pylint: disable=broad-except
            except Exception as e:
                logger.error(
                    f"Error creating user {user.username} {user.email} {user.first_name} {user.last_name} for account {account_number}: {e}"
                )
                response.created_users.append(
                    CreatedUserModel(**user.model_dump(), account_number=account_number, status="failure", error=str(e))
                )
                continue

        logger.debug(
            f"Batch user creation completed for account number: {account_number}. Created {len(response.created_users)} users."
        )
        return JsonResponse(response.model_dump())
