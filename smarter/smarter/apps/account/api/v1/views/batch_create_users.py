"""Batch user creation view for smarter api."""

from typing import List, Optional

from django.core.management import CommandError, call_command
from django.http import (
    HttpResponseBadRequest,
    JsonResponse,
)
from pydantic import BaseModel, EmailStr
from pydantic import ValidationError as PydanticValidationError
from rest_framework.request import Request

from smarter.common.utils import mask_email
from smarter.lib import logging
from smarter.lib.django.http.client_errors import (
    CLIENT_ERROR_TYPES,
    client_error_message,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .base import AccountViewBase

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


class UserFieldsModel(BaseModel):
    """The fields of a user in batch user creation that may be sent back to the client: all but the password."""

    username: str
    email: EmailStr
    first_name: str
    last_name: str
    is_admin: Optional[bool] = False


class UserModel(UserFieldsModel):
    """Pydantic model for user data in batch user creation."""

    password: Optional[str] = None


class BatchModel(BaseModel):
    """Pydantic model for batch user creation data."""

    account_number: str
    users: List[UserModel]


class CreatedUserModel(UserFieldsModel):
    """
    Pydantic model for created user data in batch user creation.

    It has no password: a response never sends one back.
    """

    account_number: str
    status: str
    error: Optional[str] = None


class BatchCreateUsersResponseModel(BaseModel):
    """Pydantic model for the response of batch user creation."""

    created_users: List[CreatedUserModel]


# pylint: disable=W0613
class BatchCreateUsersView(AccountViewBase):
    """
    Batch user creation view for smarter api.

    path: /api/v1/accounts/batch-create-users/
    """

    def get(self, request: Request, *args, **kwargs) -> HttpResponseBadRequest:
        """
        Refuse GET: users are batch created with POST.

        :param request: The request.
        :returns: A 400 response.
        """
        return HttpResponseBadRequest(
            "GET method is not allowed for this endpoint. Please use POST to batch create users."
        )

    def patch(self, request: Request, *args, **kwargs) -> HttpResponseBadRequest:
        """
        Refuse PATCH: users are batch created with POST.

        :param request: The request.
        :returns: A 400 response.
        """
        return HttpResponseBadRequest(
            "PATCH method is not allowed for this endpoint. Please use POST to batch create users."
        )

    def delete(self, request: Request, *args, **kwargs) -> HttpResponseBadRequest:
        """
        Refuse DELETE: users are batch created with POST.

        :param request: The request.
        :returns: A 400 response.
        """
        return HttpResponseBadRequest(
            "DELETE method is not allowed for this endpoint. Please use POST to batch create users."
        )

    def post(self, request: Request, *args, **kwargs) -> JsonResponse | HttpResponseBadRequest:
        """
        Handle batch user creation.

        Receives a list of user data in the
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
        :rtype: django.http.JsonResponse | django.http.HttpResponseBadRequest

        :raises django.http.HttpResponseBadRequest: If the request body is missing or invalid.
        :raises Exception: If user creation fails for any user, the error is included in the response for that user.

        .. seealso::

            - :class:`smarter.apps.account.api.v1.views.base.AccountViewBase`
            - :class:`pydantic.BaseModel`
            - :class:`django.core.management.call_command`
            - :class:`django.http.JsonResponse`
            - :class:`django.http.HttpResponseBadRequest`
            - :class:`rest_framework.request.Request`
        """
        # the users in the request may have passwords, so the request data isn't logged.
        logger.debug(
            "received a batch user creation request with %d users",
            len(request.data.get("users") or []) if isinstance(request.data, dict) else 0,
        )
        if not request.data:
            return HttpResponseBadRequest("Request body is required.")
        data = request.data
        try:
            batch_data = BatchModel.model_validate(data)
        except PydanticValidationError as e:
            # the errors leave out their input values, which may be passwords.
            problems = []
            for error in e.errors(include_input=False, include_url=False):
                location = ".".join(str(part) for part in error["loc"])
                problems.append(f"{location}: {error['msg']}")
            logger.warning("the request data is not valid: %d errors", e.error_count())
            return HttpResponseBadRequest("Invalid request data: " + "; ".join(problems))

        response = BatchCreateUsersResponseModel(created_users=[])
        account_number = batch_data.account_number
        i = 0
        for user in batch_data.users:
            i += 1
            logger.debug(
                "Processing batch user creation for account number: %s (%d/%d) users.",
                account_number,
                i,
                len(batch_data.users),
            )
            created_user = self.create_user(user, account_number)
            response.created_users.append(created_user)

        logger.debug(
            "Batch user creation completed for account number: %s. Created %d users.",
            account_number,
            len(response.created_users),
        )
        return JsonResponse(response.model_dump())

    def create_user(self, user: UserModel, account_number: str) -> CreatedUserModel:
        """
        Create one user of the batch with the ``create_user`` management command, and report the result.

        A failure is reported in the result, not raised, so that the rest of the batch is still
        created. Neither the result nor the log has the user's password.

        :param user: The user to create.
        :param account_number: The number of the account that the user joins.
        :returns: The user's fields, without the password, with a ``status`` of ``success`` or
            ``failure``, and the ``error`` of a failure.
        """
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
        user_fields = user.model_dump(exclude={"password"})

        try:
            call_command("create_user", **params)
        # create_user's refusals, e.g. an account that doesn't exist. Some of their messages
        # wrap a database error, so the response gets client_error_message()'s fixed message.
        except (CommandError,) + CLIENT_ERROR_TYPES as e:
            logger.warning(
                "could not create user %s for account %s: %s",
                mask_email(user.email),
                account_number,
                type(e).__name__,
            )
            message = client_error_message(e, "The user could not be created.")
            return CreatedUserModel(**user_fields, account_number=account_number, status="failure", error=message)
        # pylint: disable=broad-except
        except Exception:
            logger.error(
                "could not create user %s for account %s",
                mask_email(user.email),
                account_number,
                exc_info=True,
            )
            return CreatedUserModel(
                **user_fields,
                account_number=account_number,
                status="failure",
                error="An unknown error occurred while creating the user.",
            )

        return CreatedUserModel(**user_fields, account_number=account_number, status="success")
