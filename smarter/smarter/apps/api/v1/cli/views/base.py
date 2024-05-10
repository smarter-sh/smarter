"""Smarter API command-line interface Base class API view"""

import logging
from http import HTTPStatus
from typing import Dict, Union

from django.http import JsonResponse

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import smarter_admin_user_profile
from smarter.common.exceptions import SmarterExceptionBase, error_response_factory
from smarter.lib.drf.view_helpers import SmarterUnauthenticatedAPIView
from smarter.lib.manifest.broker import AbstractBroker
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.loader import SAMLoader

from ...manifests.version import SMARTER_API_VERSION
from ..brokers import BROKERS


logger = logging.getLogger(__name__)


class CliBaseApiView(SmarterUnauthenticatedAPIView):
    """
    Smarter API command-line interface Base class API view.
    - Initializes the SAMLoader and AbstractBroker instances.
    - Resolves the manifest kind and broker for the yaml manifest document.
    - Sets the user profile for the request.
    """

    _loader: SAMLoader = None
    _broker: AbstractBroker = None
    _user_profile: UserProfile = None

    @property
    def loader(self) -> SAMLoader:
        """Get the SAMLoader instance."""
        return self._loader

    @property
    def broker(self) -> AbstractBroker:
        """Get the AbstractBroker instance."""
        return self._broker

    @property
    def user_profile(self) -> UserProfile:
        """Get the UserProfile instance."""
        return self._user_profile

    def dispatch(self, request, *args, **kwargs):
        """
        The http request body is expected to contain the manifest text
        in yaml format. The manifest text is passed to the SAMLoader that will load,
        and partially validate and parse the manifest. This is then used to
        fully initialize a Pydantic manifest model. The Pydantic manifest
        model will be passed to a AbstractBroker for the manifest 'kind', which
        implements the broker service pattern for the underlying object.
        """

        # pylint: disable=W0613
        def get_user_profile(self, request) -> UserProfile:
            """Get the user profile."""

            # pylint: disable=W0511
            # TODO: setup api key authentication based on an
            # X-API-KEY header
            # return UserProfile.objects.get(user=request.user)
            logger.warning("Using smarter_admin_user_profile for user profile.")
            return smarter_admin_user_profile()

        Broker: AbstractBroker = None
        manifest_text: Union[str, Dict] = request.body.decode("utf-8")
        manifest_kind: str = None
        self._user_profile = get_user_profile(self, request)

        # 1.) ensure that we're idientifiable
        try:
            if not self.user_profile.account:
                raise SAMValidationError("Could not find account for user.")

        except SmarterExceptionBase as e:
            return JsonResponse(error_response_factory(e=e), status=HTTPStatus.BAD_REQUEST)
        # pylint: disable=W0718
        except Exception as e:
            return JsonResponse(error_response_factory(e=e), status=HTTPStatus.INTERNAL_SERVER_ERROR)

        # 2.) use the loader to retrieve the manifest 'kind'
        try:
            self._loader = SAMLoader(
                api_version=SMARTER_API_VERSION,
                kind="Plugin",
                manifest=manifest_text,
            )
        except SAMValidationError:
            # some endpoints don't require a manifest, so we
            # deal with this inside the downstream views.
            pass

        # 3.) use a manifest broker to convert the manifest text to a
        #     Pydantic model, and then use this to initialize the underlying
        #     Python object that will provide the services for the broker pattern.
        if self.loader:
            manifest_kind = self.loader.manifest_kind

            try:
                Broker = BROKERS.get(manifest_kind)
                if Broker is None:
                    raise NotImplementedError(f"Unsupported manifest kind: {manifest_kind}")
                self._broker = Broker(account_number=self.user_profile.account.account_number, manifest=manifest_text)
                if not self.broker:
                    raise SAMValidationError("Could not load manifest.")
            except SmarterExceptionBase as e:
                return JsonResponse(error_response_factory(e=e), status=HTTPStatus.BAD_REQUEST)
            # pylint: disable=W0718
            except Exception as e:
                return JsonResponse(error_response_factory(e=e), status=HTTPStatus.INTERNAL_SERVER_ERROR)

        return super().dispatch(request, *args, **kwargs)

    def handler(self, func):
        """
        Handler decorator for PluginManifestView. Provides consistent http responses
        for the view methods.
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
