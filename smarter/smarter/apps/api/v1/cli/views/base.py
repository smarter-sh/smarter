"""Smarter API command-line interface Base class API view"""

import logging
from http import HTTPStatus
from typing import Dict, Type, Union

from django.http import JsonResponse
from knox.auth import TokenAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import user_profile_for_user
from smarter.common.exceptions import SmarterExceptionBase, error_response_factory
from smarter.lib.manifest.broker import AbstractBroker
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.loader import SAMLoader

from ...manifests.version import SMARTER_API_VERSION
from ..brokers import BROKERS


logger = logging.getLogger(__name__)


class CliBaseApiView(APIView):
    """
    Smarter API command-line interface Base class API view.
    - Initializes the SAMLoader and AbstractBroker instances.
    - Resolves the manifest kind and broker for the yaml manifest document.
    - Sets the user profile for the request.
    """

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)

    _loader: SAMLoader = None
    _broker: AbstractBroker = None
    _user_profile: UserProfile = None
    _manifest_text: Union[str, Dict] = None
    _manifest_kind: str = None
    _manifest_load_failed: bool = False
    _BrokerClass: Type[AbstractBroker] = None

    @property
    def loader(self) -> SAMLoader:
        """
        Get the SAMLoader instance. a SAMLoader instance is used to load
        raw manifest text into a Pydantic model. It performs cursory validations
        on identifying keys values like the api version and kind.
        """
        if not self._loader and not self._manifest_load_failed:
            try:
                self._loader = SAMLoader(
                    api_version=SMARTER_API_VERSION,
                    manifest=self.manifest_text,
                )
                if not self._loader:
                    raise SAMValidationError("")
            except SAMValidationError:
                # some endpoints don't require a manifest, so we
                # deal with this inside the downstream views.
                self._manifest_load_failed = True

        return self._loader

    @property
    def BrokerClass(self) -> Type[AbstractBroker]:
        """
        Get the broker class for the manifest kind. This is used to
        instantiate a broker for the manifest kind.
        """
        if not self._BrokerClass:
            if self.manifest_kind:
                self._BrokerClass = BROKERS.get(self.manifest_kind)
                if not self._BrokerClass:
                    raise NotImplementedError(f"Unsupported manifest kind: {self.manifest_kind or 'None'}")
        return self._BrokerClass

    @property
    def broker(self) -> AbstractBroker:
        """
        Use a loader to try to instantiate a broker. A broker is a class that
        implements the broker service pattern. It provides a service interface
        that 'brokers' the http request for the underlying object that provides
        the object-specific service (create, update, get, delete, etc).
        """
        if self.BrokerClass and not self._broker:
            BrokerClass = self.BrokerClass
            self._broker = BrokerClass(
                api_version=SMARTER_API_VERSION,
                kind=self.manifest_kind,
                account_number=self.user_profile.account.account_number,
                manifest=self.loader.yaml_data if self.loader else None,
            )
            if not self._broker:
                raise SAMValidationError("Could not load manifest.")
        if self.manifest_kind and not self._broker:
            pass

        return self._broker

    @property
    def user_profile(self) -> UserProfile:
        return self._user_profile

    @property
    def manifest_text(self) -> Union[str, Dict]:
        return self._manifest_text

    @property
    def manifest_kind(self) -> str:
        if not self._manifest_kind:
            self._manifest_kind = self.loader.manifest_kind if self.loader else None
        return self._manifest_kind

    def dispatch(self, request, *args, **kwargs):
        """
        The http request body is expected to contain the manifest text
        in yaml format. The manifest text is passed to the SAMLoader that will load,
        and partially validate and parse the manifest. This is then used to
        fully initialize a Pydantic manifest model. The Pydantic manifest
        model will be passed to a AbstractBroker for the manifest 'kind', which
        implements the broker service pattern for the underlying object.
        """
        self._manifest_kind = str(kwargs.get("kind")).title()

        # Manifest parsing and broker instantiation are lazy implementations.
        # So for now, we'll only set the private class variable _manifest_text
        # from the request body, and then we'll leave it to the child views to
        # decide if/when to actually parse the manifest and instantiate the broker.
        self._manifest_text = request.body.decode("utf-8")
        try:
            self._user_profile = user_profile_for_user(user=request.user)
            if not self._user_profile:
                raise SAMValidationError("Could not find account for user.")
        except SmarterExceptionBase as e:
            return JsonResponse(error_response_factory(e=e), status=HTTPStatus.FORBIDDEN)

        return super().dispatch(request, *args, **kwargs)

    def handler(self, func):
        """
        wrapper handler for child view verb implementations: get, post, put, delete, etc.
        Provides consistent http responses for the view methods. Works like a diffy
        in javascript, where the function is passed as an argument to the wrapper.

        Usage:
            def post(self, request):
                return self.handler(self.function_that_returns_JsonResponse)()
        """

        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except NotImplementedError as e:
                return JsonResponse(error_response_factory(e=e), status=HTTPStatus.NOT_IMPLEMENTED)
            except SmarterExceptionBase as e:
                return JsonResponse(error_response_factory(e=e), status=HTTPStatus.BAD_REQUEST)
            # pylint: disable=W0718
            except Exception as e:
                return JsonResponse(error_response_factory(e=e), status=HTTPStatus.INTERNAL_SERVER_ERROR)

        return wrapper
