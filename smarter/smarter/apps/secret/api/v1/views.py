"""Secret API views."""

from django.db.models import QuerySet
from django.http.response import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.account.models import User, UserProfile
from smarter.apps.secret.models import Secret
from smarter.apps.secret.serializers import SecretSerializer
from smarter.common.utils import is_authenticated_request, smarter_build_absolute_uri
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAdminAPIView,
    SmarterAdminListAPIView,
)
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.SECRET_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


def secrets_for_user(user) -> QuerySet[Secret]:
    """The Secrets that belong to any of the user's accounts."""
    if not isinstance(user, User):
        return Secret.objects.none()
    accounts = UserProfile.objects.filter(user=user).values("account")
    return Secret.objects.filter(user_profile__account__in=accounts)


class SecretView(SmarterAdminAPIView):
    """Class for secret views."""

    serializer_class = SecretSerializer

    def get_queryset(self):
        return secrets_for_user(self.request.user)

    def get(self, request: Request, secret_id: int, *args, **kwargs):
        """Return the Secret, without its value."""
        secret = get_object_or_404(self.get_queryset(), pk=secret_id)
        return Response(SecretSerializer(secret).data)

    def post(self, request: Request, secret_id: int, *args, **kwargs):
        """Same as get().

        Smarter detail views are also served by POST.
        """
        return self.get(request, secret_id, *args, **kwargs)


class SecretListView(SmarterAdminListAPIView):
    """Class for secret list views."""

    serializer_class = SecretSerializer

    def get_queryset(self):
        return secrets_for_user(self.request.user)

    def dispatch(self, request: Request, *args, **kwargs):
        try:
            response = super().dispatch(request, *args, **kwargs)
        except AttributeError:
            # catches an error raised by a decorator elsewhere in the stack that
            # barfs when the user object is None
            # File "/home/smarter_user/venv/lib/python3.12/site-packages/django/contrib/admin/views/decorators.py", line 13, in <lambda>
            return HttpResponseForbidden("Forbidden: Invalid or missing authentication credentials.")

        logger.info(
            "%s.dispatch() - request: %s, user: %s",
            self.formatted_class_name,
            request,
            request.user.username if request.user else "Anonymous",  # type: ignore[assignment]
        )
        return response

    def setup(self, request: Request, *args, **kwargs):
        """Setup the view.

        This is called by Django before dispatch() and is used to set up the view for the request.
        """
        super().setup(request, *args, **kwargs)
        if not hasattr(self.request, "user") or not isinstance(self.request.user, User):
            logger.warning(
                "%s.setup() - request has no user or user is not an instance of User: %s",
                self.formatted_class_name,
                self.request.user,
            )
        else:
            if not is_authenticated_request(self.request):
                logger.warning(
                    "%s.setup() - request user is not authenticated: %s",
                    self.formatted_class_name,
                    self.request.user,
                )
        logger.info(
            "%s.setup() - request: %s, user: %s, user_profile: %s is_authenticated: %s",
            self.formatted_class_name,
            smarter_build_absolute_uri(self.request),
            self.request.user.username if self.request.user else "Anonymous",  # type: ignore[assignment]
            self.user_profile,
            is_authenticated_request(self.request),
        )
