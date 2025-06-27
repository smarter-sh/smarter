# pylint: disable=W0707,W0718
"""Account Payment method views for smarter api."""
import json
import logging
from http import HTTPStatus
from typing import Optional

from django.core.exceptions import ValidationError
from django.core.handlers.wsgi import WSGIRequest
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from smarter.apps.account.models import (
    Account,
    PaymentMethod,
    User,
    UserProfile,
    get_resolved_user,
)
from smarter.apps.account.serializers import PaymentMethodSerializer
from smarter.apps.account.utils import get_cached_account_for_user

from .base import AccountListViewBase, AccountViewBase


logger = logging.getLogger(__name__)


class PaymentMethodView(AccountViewBase):
    """Payment method view for smarter api."""

    def get(self, request, payment_method_id: Optional[int] = None):
        return get_payment_method(request, payment_method_id)

    def post(self, request):
        return create_payment_method(request)

    def patch(self, request):
        return update_payment_method(request)

    def delete(self, request, payment_method_id: Optional[int] = None):
        return delete_payment_method(request, payment_method_id)


class PaymentMethodsListView(AccountListViewBase):
    """Payment methods list view for smarter api."""

    serializer_class = PaymentMethodSerializer

    def get_queryset(self):
        user = get_resolved_user(self.request.user)
        if user is None or user.is_superuser or user.is_staff:
            account = get_object_or_404(UserProfile, user=self.request.user).account
            return PaymentMethod.objects.filter(account=account)
        return HttpResponse("Unauthorized", status=HTTPStatus.UNAUTHORIZED.value)


# -----------------------------------------------------------------------
# handlers for users
# -----------------------------------------------------------------------
def validate_request_body(request):
    # do a cursory check of the request data
    try:
        if not isinstance(request.data, dict):
            raise ValidationError(
                f"Invalid request data. Was expecting a dictionary but received {type(request.data)}."
            )
    except ValidationError as e:
        return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST.value)
    except Exception as e:
        return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST.value)
    return None


def get_payment_method(request, payment_method_id: int):
    payment_method: PaymentMethod
    account: Optional[Account]

    user = get_resolved_user(request.user)
    if user is None:
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED.value)
    if not user.is_superuser and not user.is_staff:
        return JsonResponse({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED.value)

    try:
        payment_method = PaymentMethod.objects.get(id=payment_method_id)
        account = payment_method.account
    except PaymentMethod.DoesNotExist:
        return JsonResponse({"error": "Payment method not found"}, status=HTTPStatus.NOT_FOUND.value)

    user = get_resolved_user(request.user)
    if user is None:
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED.value)
    account = get_cached_account_for_user(user=user)

    # staff can manage payment methods for their account
    if isinstance(request.user, User) and request.user.is_superuser or (account == account and request.user.is_staff):
        serializer = PaymentMethodSerializer(payment_method)
        return Response(serializer.data, status=HTTPStatus.OK.value)

    return JsonResponse(
        {"error": "You are not authorized to modify this account."}, status=HTTPStatus.UNAUTHORIZED.value
    )


def create_payment_method(request: WSGIRequest):
    """Create an account from a json representation in the body of the request."""
    account: Account
    data: dict

    user = get_resolved_user(request.user)
    if user is None:
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED.value)

    if not user.is_superuser and not user.is_staff:
        return JsonResponse({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED.value)

    validate_request_body(request)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format in request body."}, status=HTTPStatus.BAD_REQUEST.value)

    # the new payment method will be associated with the account of the current user
    try:
        account = UserProfile.objects.get(user=request.user).account
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User is not associated with any account."}, status=HTTPStatus.UNAUTHORIZED.value)

    try:
        data["account"] = account
        payment_method = PaymentMethod.objects.create(**data)
    except Exception as e:
        return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST.value)

    return HttpResponseRedirect(request.path_info + str(payment_method.id) + "/")  # type: ignore[return-value]


def update_payment_method(request: WSGIRequest):
    """update an account from a json representation in the body of the request."""
    data: dict
    payment_method_to_update: Optional[User] = None

    user = get_resolved_user(request.user)
    if user is None:
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED.value)
    if not user.is_superuser and not user.is_staff:
        return JsonResponse({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED.value)

    validate_request_body(request)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format in request body."}, status=HTTPStatus.BAD_REQUEST.value)
    if not isinstance(data, dict):
        return JsonResponse(
            {"error": "Invalid request data. Was expecting a dictionary."}, status=HTTPStatus.BAD_REQUEST.value
        )

    try:
        payment_method = PaymentMethod.objects.get(id=data.get("id"))
        account = payment_method.account
    except PaymentMethod.DoesNotExist:
        return JsonResponse({"error": "Payment method not found"}, status=HTTPStatus.NOT_FOUND.value)

    if isinstance(request.user, User):
        account = get_cached_account_for_user(user=request.user)

    # superusers can manage any payment method. staff can manage payment methods for their account
    if isinstance(request.user, User) and not (
        request.user.is_superuser or (account == account and request.user.is_staff)
    ):
        return JsonResponse(
            {"error": "You are not authorized to modify this account."}, status=HTTPStatus.UNAUTHORIZED.value
        )

    try:
        for key, value in data.items():
            if hasattr(payment_method_to_update, key):
                setattr(payment_method_to_update, key, value)
        payment_method_to_update.save()
    except ValidationError as e:
        return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        return JsonResponse(
            {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR.value
        )

    return HttpResponseRedirect(request.path_info)


def delete_payment_method(request: WSGIRequest, payment_method_id: Optional[int] = None):
    """delete a plugin by id."""

    user = get_resolved_user(request.user)
    if user is None:
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED.value)
    if not user.is_superuser and not user.is_staff:
        return JsonResponse({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED.value)

    try:
        if payment_method_id:
            account = Account.objects.get(id=payment_method_id)
        else:
            account = UserProfile.objects.get(user=request.user).account
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED.value)

    try:
        with transaction.atomic():
            account.delete()
            UserProfile.objects.get(user=request.user).delete()
    except Exception as e:
        return JsonResponse(
            {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR.value
        )

    plugins_path = request.path_info.rsplit("/", 2)[0]
    return HttpResponseRedirect(plugins_path)
