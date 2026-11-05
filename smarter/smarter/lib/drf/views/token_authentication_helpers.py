"""Django template and view helper functions for knox token authentication."""

from functools import cached_property
from typing import Union

from django.http import HttpResponseBase, HttpResponseForbidden
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from smarter.apps.api.signals import api_request_completed, api_request_initiated
from smarter.common.utils import is_authenticated_request
from smarter.lib import logging
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.token_authentication import SmarterTokenAuthentication
from smarter.lib.drf.views.helpers import SmarterAuthenticatedPermissionClass

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.API_LOGGING])


# ------------------------------------------------------------------------------
# API Authenticated Views
# ------------------------------------------------------------------------------


class SmarterAuthenticatedAPIView(APIView, SmarterRequestMixin):
    """
    Smarter base class for DRF API detail views that require authentication.

    Does the following:

    - Adds SmarterRequestMixin to the view, so that base Smarter functionality is available to all subclasses.
    - Adds SmarterTokenAuthentication to the default SessionAuthentication for authentication.
    - Overrides Django's logic for initializing the request object to ensure that SmarterRequestMixin is fully initialized before any other logic runs.
    """

    permission_classes = [SmarterAuthenticatedPermissionClass]
    authentication_classes = [SmarterTokenAuthentication, SessionAuthentication]

    def get_permissions(self):
        """
        Return the view's permissions, none for an OPTIONS request.

        OPTIONS requests (CORS preflight, DRF metadata probes) never carry credentials, so they
        don't require authentication.

        :returns: The permission instances, or an empty list for an OPTIONS request.
        """
        if getattr(self, "request", None) is not None and self.request.method == "OPTIONS":
            return []
        return super().get_permissions()

    def __init__(self, *args, **kwargs):
        """
        Initialize the view, and its SmarterRequestMixin.

        :param args: Passed to the view and to SmarterRequestMixin.
        :param kwargs: Passed to the view. ``request``, ``user``, ``account`` and ``user_profile``
            are passed to SmarterRequestMixin.
        """
        super().__init__(*args, **kwargs)
        self.request = kwargs.pop("request", None)
        user = kwargs.pop("user", None)
        account = kwargs.pop("account", None)
        user_profile = kwargs.pop("user_profile", None)
        SmarterRequestMixin.__init__(
            self, request=self.request, user=user, account=account, user_profile=user_profile, *args, **kwargs
        )

    @cached_property
    def formatted_class_name(self):
        """The view's dotted class name, formatted for log messages."""
        class_name = f"{__name__}.{SmarterAuthenticatedAPIView.__name__}"
        return self.formatted_text(class_name)

    def setup(self, request: Request, *args, **kwargs):
        """
        Set up the view for the request, and send the ``api_request_initiated`` signal.

        Django calls this before ``dispatch()``.

        :param request: The incoming HTTP request.
        :param args: Passed to DRF's ``setup()``.
        :param kwargs: Passed to DRF's ``setup()``.
        """
        # drf setup logic
        super().setup(request, *args, **kwargs)

        # go through our own request and account mixin setup logic
        self.smarter_request = request

        # overwrite the request object with our smarter_request object
        if not self.smarter_request:
            logger.warning(
                "%s.setup() - smarter_request is None after setting it to request: %s",
                self.formatted_class_name,
                request,
            )
        self.request = self.smarter_request
        api_request_initiated.send(sender=self.__class__, instance=self, request=request)

    def initial(self, request: Request, *args, **kwargs):
        """
        Finish initializing SmarterRequestMixin with the DRF request, then run DRF's ``initial()``.

        This is the earliest point in the DRF view lifecycle where the request object is available.
        Up to this point our SmarterRequestMixin, and AccountMixin classes are only partially
        initialized. This method takes care of the rest of the initialization.

        :param request: The incoming HTTP request.
        :param args: Passed to DRF's ``initial()``.
        :param kwargs: Passed to DRF's ``initial()``.
        """
        if not self.srm_ready and self.smarter_request is not request:
            self.smarter_request = request
        super().initial(self.request, *args, **kwargs)


class SmarterAuthenticatedListAPIView(ListAPIView, SmarterRequestMixin):
    """
    Smarter base class for DRF API list views that require authentication.

    Does the following:

    - Adds SmarterRequestMixin to the view, so that base Smarter functionality is available to all subclasses.
    - Adds SmarterTokenAuthentication to the default SessionAuthentication for authentication.
    - Overrides Django's logic for initializing the request object to ensure that SmarterRequestMixin is fully initialized before any other logic runs.
    """

    permission_classes = [SmarterAuthenticatedPermissionClass]
    authentication_classes = [SmarterTokenAuthentication, SessionAuthentication]

    def get_permissions(self):
        """
        Return the view's permissions, none for an OPTIONS request.

        OPTIONS requests (CORS preflight, DRF metadata probes) never carry credentials, so they
        don't require authentication.

        :returns: The permission instances, or an empty list for an OPTIONS request.
        """
        if getattr(self, "request", None) is not None and self.request.method == "OPTIONS":
            return []
        return super().get_permissions()

    def __init__(self, *args, **kwargs):
        """
        Initialize the view, and its SmarterRequestMixin.

        DRF/Django's ``View.__init__()`` does not call ``super().__init__()``, so without this,
        ``SmarterRequestMixin.__init__()`` (and thus ``self._srm_ready`` and friends) would never
        be invoked, causing an AttributeError the first time ``self.srm_ready`` is accessed.

        :param args: Passed to the view and to SmarterRequestMixin.
        :param kwargs: Passed to the view. ``request``, ``user``, ``account`` and ``user_profile``
            are passed to SmarterRequestMixin.
        """
        super().__init__(*args, **kwargs)
        self.request = kwargs.pop("request", None)
        user = kwargs.pop("user", None)
        account = kwargs.pop("account", None)
        user_profile = kwargs.pop("user_profile", None)
        SmarterRequestMixin.__init__(
            self, request=self.request, user=user, account=account, user_profile=user_profile, *args, **kwargs
        )

    @cached_property
    def formatted_class_name(self):
        """The view's dotted class name, formatted for log messages."""
        class_name = f"{__name__}.{SmarterAuthenticatedListAPIView.__name__}"
        return self.formatted_text(class_name)

    def initial(self, request: Request, *args, **kwargs):
        """
        Set the SmarterRequestMixin's request to the DRF request, then run DRF's ``initial()``.

        :param request: The incoming HTTP request.
        :param args: Passed to DRF's ``initial()``.
        :param kwargs: Passed to DRF's ``initial()``.
        """
        # setting the same request again would only rebuild every cached property.
        if self.smarter_request is not request:
            self.smarter_request = request
        super().initial(self.request, *args, **kwargs)


# ------------------------------------------------------------------------------
# Admin API Views
# ------------------------------------------------------------------------------
class SmarterAdminAPIMixin(SmarterRequestMixin):
    """Mixin for admin API views, with checks of whether the authenticated user is a superuser or staff."""

    request: Request

    def is_superuser(self) -> bool:
        """
        Return whether the request is authenticated, and its user is a superuser.

        :returns: True if the user is a superuser, False otherwise.
        """
        if not is_authenticated_request(self.request):
            logger.warning(
                "%s.is_superuser() - request user is not authenticated: %s",
                self.formatted_class_name,
                self.request.user,
            )
            return False
        if not self.user_profile:
            return False
        if not self.user_profile.user.is_superuser:
            return False
        return True

    def check_superuser(self) -> None:
        """
        Refuse the request unless the authenticated user is a superuser.

        :raises PermissionDenied: If the authenticated user is not a superuser.
        """
        if not self.is_superuser():
            raise PermissionDenied(f"User {self.user_profile} does not have superuser privileges.")

    def is_staff(self) -> bool:
        """
        Return whether the request is authenticated, and its user is staff or a superuser.

        :returns: True if the user is staff or a superuser, False otherwise.
        """
        if not is_authenticated_request(self.request):
            logger.warning(
                "%s.is_staff() - request user is not authenticated: %s",
                self.formatted_class_name,
                self.request.user,
            )
            return False
        if not self.user_profile:
            return False
        user = self.user_profile.user
        if not user.is_staff and not user.is_superuser:
            return False
        return True


class SmarterAdminAPIView(APIView, SmarterAdminAPIMixin):
    """
    Smarter base class for DRF API views that only superusers may use.

    Does the following:

    - Adds SmarterRequestMixin to the view, so that base Smarter functionality is available to all subclasses.
    - Adds SmarterTokenAuthentication to the default SessionAuthentication for authentication.
    - Overrides Django's logic for initializing the request object to ensure that
      SmarterRequestMixin is fully initialized before any other logic runs.
    - Limits access to superusers, in ``initial()``.
    """

    permission_classes = [SmarterAuthenticatedPermissionClass]
    authentication_classes = [SmarterTokenAuthentication, SessionAuthentication]

    @cached_property
    def formatted_class_name(self):
        """The view's dotted class name, formatted for log messages."""
        class_name = f"{__name__}.{SmarterAdminAPIView.__name__}"
        return self.formatted_text(class_name)

    def __init__(self, *args, **kwargs):
        """
        Initialize the view, and its SmarterRequestMixin.

        :param args: Passed to the view and to SmarterRequestMixin.
        :param kwargs: Passed to the view. ``request``, ``user``, ``account`` and ``user_profile``
            are passed to SmarterRequestMixin.
        """
        super().__init__(*args, **kwargs)
        request = kwargs.pop("request", None)
        user = kwargs.pop("user", None)
        account = kwargs.pop("account", None)
        user_profile = kwargs.pop("user_profile", None)
        SmarterRequestMixin.__init__(
            self, request=request, user=user, account=account, user_profile=user_profile, *args, **kwargs
        )

    def setup(self, request: Request, *args, **kwargs) -> None:
        """
        Set up the view and its SmarterRequestMixin, and send the ``api_request_initiated`` signal.

        Django calls this before ``dispatch()``.

        :param request: The incoming HTTP request.
        :param args: Passed to DRF's ``setup()`` and to SmarterRequestMixin.
        :param kwargs: Passed to DRF's ``setup()``. ``user``, ``account`` and ``user_profile`` are
            passed to SmarterRequestMixin.
        """
        user = kwargs.pop("user", None)
        account = kwargs.pop("account", None)
        user_profile = kwargs.pop("user_profile", None)
        super().setup(request, *args, **kwargs)
        SmarterRequestMixin.__init__(
            self, request=request, user=user, account=account, user_profile=user_profile, *args, **kwargs
        )

        # note: setup() is the earliest point in the request lifecycle where we can
        # send signals.
        api_request_initiated.send(sender=self.__class__, instance=self, request=request)

    def initial(self, request: Request, *args, **kwargs):
        """
        Run DRF's ``initial()``, then refuse the request unless its user is a superuser.

        The check runs here, after DRF has authenticated the request, so that a
        request authenticated with an api key, rather than a session, is recognized.

        :param request: The incoming HTTP request.
        :param args: Passed to DRF's ``initial()``.
        :param kwargs: Passed to DRF's ``initial()``.
        :raises PermissionDenied: If the authenticated user is not a superuser.
        """
        super().initial(request, *args, **kwargs)
        self.check_superuser()

    def dispatch(self, request: Request, *args, **kwargs) -> Union[HttpResponseBase, HttpResponseForbidden, Response]:
        """
        Dispatch the request as DRF does, turning the AttributeError of a missing user into a 403.

        The ``api_request_completed`` signal is sent by :meth:`finalize_response`, which DRF's
        dispatch() calls, so that it is sent once per request.

        :param request: The incoming HTTP request.
        :param args: Passed to DRF's ``dispatch()``.
        :param kwargs: Passed to DRF's ``dispatch()``.
        :returns: The view's response, or a 403 if the user is missing.
        """
        try:
            return super().dispatch(request, *args, **kwargs)
        # pylint: disable=broad-except
        except AttributeError:
            # catches an error raised by a decorator elsewhere in the stack that
            # barfs when the user object is None
            # File "/home/smarter_user/venv/lib/python3.12/site-packages/django/contrib/admin/views/decorators.py", line 13, in <lambda>
            return HttpResponseForbidden("Forbidden: Invalid or missing authentication credentials.")

    def finalize_response(self, request: Request, response: Response, *args, **kwargs) -> Response:
        """
        Send the ``api_request_completed`` signal, then finalize the response as DRF does.

        :param request: The incoming HTTP request.
        :param response: The outgoing HTTP response.
        :param args: Passed to DRF's ``finalize_response()``.
        :param kwargs: Passed to DRF's ``finalize_response()``.
        :returns: The finalized response.
        """
        api_request_completed.send(sender=self.__class__, instance=self, request=request, response=response)
        return super().finalize_response(request, response, *args, **kwargs)


class SmarterAdminListAPIView(ListAPIView, SmarterAdminAPIMixin):
    """
    Smarter base class for DRF list views that only superusers may use.

    Does the following:

    - Adds SmarterRequestMixin to the view, so that base Smarter functionality is available to all subclasses.
    - Adds SmarterTokenAuthentication to the default SessionAuthentication for authentication.
    - Overrides Django's logic for initializing the request object to ensure that
      SmarterRequestMixin is fully initialized before any other logic runs.
    - Limits access to superusers, in ``initial()``.
    """

    permission_classes = [SmarterAuthenticatedPermissionClass]
    authentication_classes = [SmarterTokenAuthentication, SessionAuthentication]

    def __init__(self, *args, **kwargs):
        """
        Initialize the view, and its SmarterRequestMixin.

        :param args: Passed to the view and to SmarterRequestMixin.
        :param kwargs: Passed to the view. ``request``, ``user``, ``account`` and ``user_profile``
            are passed to SmarterRequestMixin.
        """
        super().__init__(*args, **kwargs)
        request = kwargs.pop("request", None)
        user = kwargs.pop("user", None)
        account = kwargs.pop("account", None)
        user_profile = kwargs.pop("user_profile", None)
        SmarterRequestMixin.__init__(
            self, request=request, user=user, account=account, user_profile=user_profile, *args, **kwargs
        )

    @cached_property
    def formatted_class_name(self):
        """The view's dotted class name, formatted for log messages."""
        class_name = f"{__name__}.{SmarterAdminListAPIView.__name__}"
        return self.formatted_text(class_name)

    def setup(self, request: Request, *args, **kwargs):
        """
        Set up the view and its SmarterRequestMixin, and send the ``api_request_initiated`` signal.

        Django calls this before ``dispatch()``.

        :param request: The incoming HTTP request.
        :param args: Passed to DRF's ``setup()`` and to SmarterRequestMixin.
        :param kwargs: Passed to DRF's ``setup()`` and to SmarterRequestMixin.
        """
        super().setup(request, *args, **kwargs)
        user = kwargs.pop("user", None)
        account = kwargs.pop("account", None)
        user_profile = kwargs.pop("user_profile", None)
        SmarterRequestMixin.__init__(
            self, request=request, user=user, account=account, user_profile=user_profile, *args, **kwargs
        )
        # note: setup() is the earliest point in the request lifecycle where we can
        # send signals.
        api_request_initiated.send(sender=self.__class__, instance=self, request=request)

    def initial(self, request: Request, *args, **kwargs):
        """
        Run DRF's ``initial()``, then refuse the request unless its user is a superuser.

        The check runs here, after DRF has authenticated the request, so that a
        request authenticated with an api key, rather than a session, is recognized.

        :param request: The incoming HTTP request.
        :param args: Passed to DRF's ``initial()``.
        :param kwargs: Passed to DRF's ``initial()``.
        :raises PermissionDenied: If the authenticated user is not a superuser.
        """
        super().initial(request, *args, **kwargs)
        self.check_superuser()

    def dispatch(self, request: Request, *args, **kwargs):
        """
        Dispatch the request as DRF does, turning the AttributeError of a missing user into a 403.

        The AttributeError is logged at ERROR, with its traceback.

        :param request: The incoming HTTP request.
        :param args: Passed to DRF's ``dispatch()``.
        :param kwargs: Passed to DRF's ``dispatch()``.
        :returns: The view's response, or a 403 if the user is missing.
        """
        try:
            response = super().dispatch(request, *args, **kwargs)
        except AttributeError as e:
            logger.error(
                "%s.dispatch() - encountered AttributeError: %s.",
                self.formatted_class_name,
                str(e),
                exc_info=True,
            )
            # catches an error raised by a decorator elsewhere in the stack that
            # barfs when the user object is None
            # File "/home/smarter_user/venv/lib/python3.12/site-packages/django/contrib/admin/views/decorators.py", line 13, in <lambda>
            return HttpResponseForbidden("Forbidden: Invalid or missing authentication credentials.")
        return response

    def finalize_response(self, request: Request, response: Response, *args, **kwargs):
        """
        Send the ``api_request_completed`` signal, then finalize the response as DRF does.

        :param request: The incoming HTTP request.
        :param response: The outgoing HTTP response.
        :param args: Passed to DRF's ``finalize_response()``.
        :param kwargs: Passed to DRF's ``finalize_response()``.
        :returns: The finalized response.
        """
        api_request_completed.send(sender=self.__class__, instance=self, request=request, response=response)
        return super().finalize_response(request, response, *args, **kwargs)
