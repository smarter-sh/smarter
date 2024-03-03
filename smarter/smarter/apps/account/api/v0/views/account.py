# -*- coding: utf-8 -*-
# pylint: disable=W0707,W0718
"""Account views for smarter api."""
from http import HTTPStatus

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import Http404, HttpResponseRedirect, JsonResponse
from knox.auth import TokenAuthentication
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.serializers import AccountSerializer


class AccountView(APIView):
    """Account view for smarter api."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def get(self, request, account_number: str = None):
        return get_account(request, account_number)

    def post(self, request):
        return create_account(request)

    def patch(self, request, account_number: str = None):
        return update_account(request, account_number)

    def delete(self, request, account_number: str = None):
        return delete_account(request, account_number)

    def handle_exception(self, exc):
        if isinstance(exc, Http404):
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        if isinstance(exc, PermissionDenied):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        return Response({"error": "Invalid HTTP method"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


class AccountListView(ListAPIView):
    """Account list view for smarter api."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Account.objects.all()

        if self.request.user.is_staff:
            try:
                return UserProfile.objects.get(user=self.request.user).account
            except UserProfile.DoesNotExist:
                return Response({"error": "User not found"}, status=HTTPStatus.NOT_FOUND)
        return Response({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)


# -----------------------------------------------------------------------
# handlers for accounts
# -----------------------------------------------------------------------
def get_account(request, account_id: int = None):
    """Get an account json representation by id."""
    try:
        if account_id:
            account = Account.objects.get(id=account_id)
        else:
            account = UserProfile.objects.get(user=request.user).account
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    serializer = AccountSerializer(account)
    return Response(serializer.data, status=HTTPStatus.OK)


def create_account(request):
    """Create an account from a json representation in the body of the request."""
    data: dict = None

    try:
        data = request.data
        with transaction.atomic():
            account = Account.objects.create(**data)
            UserProfile.objects.create(user=request.user, account=account)
    except Exception as e:
        return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)

    return HttpResponseRedirect(request.path_info + str(account.id) + "/")


def update_account(request, account_id: int = None):
    """update an account from a json representation in the body of the request."""
    account: Account = None
    data: dict = None

    try:
        if account_id:
            account = Account.objects.get(id=account_id)
        else:
            account = UserProfile.objects.get(user=request.user).account
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED)

    try:
        data = request.data
        if not isinstance(data, dict):
            return JsonResponse(
                {"error": f"Invalid request data. Expected a JSON dict in request body but received {type(data)}"},
                status=HTTPStatus.BAD_REQUEST,
            )
    except Exception as e:
        return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)

    try:
        for key, value in data.items():
            if hasattr(account, key):
                setattr(account, key, value)
        account.save()
    except ValidationError as e:
        return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        return JsonResponse({"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    return HttpResponseRedirect(request.path_info)


def delete_account(request, account_id: int = None):
    """delete a plugin by id."""
    try:
        if account_id:
            account = Account.objects.get(id=account_id)
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
