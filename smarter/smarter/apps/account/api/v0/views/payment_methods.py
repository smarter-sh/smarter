# -*- coding: utf-8 -*-
# pylint: disable=W0707,W0718
"""Account Payment method views for smarter api."""
from http import HTTPStatus

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from knox.auth import TokenAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from smarter.apps.account.models import Account, PaymentMethod, UserProfile
from smarter.apps.account.serializers import PaymentMethodSerializer


@api_view(["GET", "POST", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication, SessionAuthentication])
def payment_method_view(request, payment_method_id: int = None):
    if request.method == "GET":
        return get_payment_method(request, payment_method_id)
    if request.method == "POST":
        return create_payment_method(request)
    if request.method == "PATCH":
        return update_payment_method(request)
    if request.method == "DELETE":
        return delete_payment_method(request, payment_method_id)
    return JsonResponse({"error": "Invalid HTTP method"}, status=405)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication, SessionAuthentication])
def payment_methods_list_view(request):
    """Get a json list[dict] of all payment methods for the account."""
    if request.user.is_superuser or request.user.is_staff:
        try:
            account = UserProfile.objects.get(user=request.user).account
        except UserProfile.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED)
    else:
        return JsonResponse({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)

    payment_methods = PaymentMethod.objects.filter(account=account)
    serializer = PaymentMethodSerializer(payment_methods, many=True)
    return Response(serializer.data, status=HTTPStatus.OK)


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
        return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
    return None


def get_payment_method(request, payment_method_id: int):
    payment_method: PaymentMethod = None
    account: Account = None

    if not request.user.is_superuser and not request.user.is_staff:
        return JsonResponse({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)

    try:
        payment_method = PaymentMethod.objects.get(id=payment_method_id)
        account = payment_method.account
    except PaymentMethod.DoesNotExist:
        return JsonResponse({"error": "Payment method not found"}, status=HTTPStatus.NOT_FOUND)

    user_profile = UserProfile.objects.get(user=request.user)

    # staff can manage payment methods for their account
    if request.user.is_superuser or (user_profile.account == account and request.user.is_staff):
        serializer = PaymentMethodSerializer(payment_method)
        return Response(serializer.data, status=HTTPStatus.OK)

    return JsonResponse({"error": "You are not authorized to modify this account."}, status=HTTPStatus.UNAUTHORIZED)


def create_payment_method(request):
    """Create an account from a json representation in the body of the request."""
    account: Account = None
    data: dict = None

    if not request.user.is_superuser and not request.user.is_staff:
        return JsonResponse({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)

    validate_request_body(request)
    data = request.data

    # the new payment method will be associated with the account of the current user
    try:
        account = UserProfile.objects.get(user=request.user).account
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User is not associated with any account."}, status=HTTPStatus.UNAUTHORIZED)

    try:
        data["account"] = account
        payment_method = PaymentMethod.objects.create(**data)
    except Exception as e:
        return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)

    return HttpResponseRedirect(request.path_info + str(payment_method.id) + "/")


def update_payment_method(request):
    """update an account from a json representation in the body of the request."""
    data: dict = None
    payment_method_to_update: User = None

    if not request.user.is_superuser and not request.user.is_staff:
        return JsonResponse({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)

    validate_request_body(request)
    data = request.data

    try:
        payment_method = PaymentMethod.objects.get(id=request.data.get("id"))
        account = payment_method.account
    except PaymentMethod.DoesNotExist:
        return JsonResponse({"error": "Payment method not found"}, status=HTTPStatus.NOT_FOUND)

    user_profile = UserProfile.objects.get(user=request.user)

    # superusers can manage any payment method. staff can manage payment methods for their account
    if not (request.user.is_superuser or (user_profile.account == account and request.user.is_staff)):
        return JsonResponse({"error": "You are not authorized to modify this account."}, status=HTTPStatus.UNAUTHORIZED)

    try:
        for key, value in data.items():
            if hasattr(payment_method_to_update, key):
                setattr(payment_method_to_update, key, value)
        payment_method_to_update.save()
    except ValidationError as e:
        return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        return JsonResponse({"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    return HttpResponseRedirect(request.path_info)


def delete_payment_method(request, payment_method_id: int = None):
    """delete a plugin by id."""

    if not request.user.is_superuser and not request.user.is_staff:
        return JsonResponse({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)

    try:
        if payment_method_id:
            account = Account.objects.get(id=payment_method_id)
        else:
            account = UserProfile.objects.get(user=request.user).account
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED)

    try:
        with transaction.atomic():
            account.delete()
            UserProfile.objects.get(user=request.user).delete()
    except Exception as e:
        return JsonResponse({"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    plugins_path = request.path_info.rsplit("/", 2)[0]
    return HttpResponseRedirect(plugins_path)
