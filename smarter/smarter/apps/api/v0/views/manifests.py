# pylint: disable=W0613
"""This module contains the PluginManifestView for the smarter api."""

from http import HTTPStatus
from typing import Dict, Type, Union

from django.http import HttpResponse, JsonResponse

from smarter.apps.account.models import UserProfile
from smarter.apps.api.v0.manifests.broker import SAMBroker
from smarter.apps.api.v0.manifests.enum import SAMKinds
from smarter.apps.api.v0.manifests.exceptions import SAMValidationError
from smarter.apps.api.v0.manifests.loader import SAMLoader
from smarter.apps.plugin.api.v0.manifests.broker import SAMPluginBroker
from smarter.common.exceptions import SmarterExceptionBase, error_response_factory
from smarter.lib.drf.view_helpers import SmarterAuthenticatedAPIView


BROKERS: Dict[str, Type[SAMBroker]] = {
    SAMKinds.PLUGIN.value: SAMPluginBroker,
    SAMKinds.ACCOUNT.value: None,
    SAMKinds.USER.value: None,
    SAMKinds.CHAT.value: None,
    SAMKinds.CHATBOT.value: None,
}


class ManifestApiView(SmarterAuthenticatedAPIView):
    """PluginStatic manifest view for smarter api."""

    _loader: SAMLoader = None
    _broker: SAMBroker = None
    _user_profile: UserProfile = None

    @property
    def loader(self) -> SAMLoader:
        """Get the SAMLoader instance."""
        return self._loader

    @property
    def broker(self) -> SAMBroker:
        """Get the SAMBroker instance."""
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
        model will be passed to a SAMBroker for the manifest 'kind', which
        implements the broker service pattern for the underlying object.
        """

        def get_user_profile(self, request) -> UserProfile:
            """Get the user profile."""

            # pylint: disable=W0511
            # TODO: setup api key authentication based on an
            # X-API-KEY header
            return UserProfile.objects.get(user=request.user)

        Broker: SAMBroker = None
        manifest_text: Union[str, Dict] = request.body.decode("utf-8")
        manifest_kind: str = None
        self._user_profile = get_user_profile(self, request)

        # 1.) use the loader to retrieve the manifest 'kind'
        try:
            if not self.user_profile.account:
                raise SAMValidationError("Could not find account for user.")
            self._loader = SAMLoader(account_number=self.user_profile.account.account_number, manifest=manifest_text)
            if not self.loader:
                raise SAMValidationError("Could not load manifest.")
        except SmarterExceptionBase as e:
            return JsonResponse(error_response_factory(e=e), status=HTTPStatus.BAD_REQUEST)
        # pylint: disable=W0718
        except Exception as e:
            return JsonResponse(error_response_factory(e=e), status=HTTPStatus.INTERNAL_SERVER_ERROR)

        manifest_kind = self.loader.manifest_kind

        # 2.) use a manifest broker to convert the manifest text to a
        #     Pydantic model, and then use this to initialize the underlying
        #     Python object that will provide the services for the broker pattern.
        try:
            Broker = BROKERS.get(manifest_kind)
            if Broker is None:
                raise SAMValidationError(f"Unsupported manifest kind: {manifest_kind}")
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
        """Handler decorator for PluginManifestView."""

        def wrapper(*args, **kwargs):
            try:
                retval = func(*args, **kwargs)
                if isinstance(retval, dict):
                    return JsonResponse(retval, status=HTTPStatus.OK)
                return HttpResponse(status=HTTPStatus.OK)
            except NotImplementedError as e:
                return JsonResponse(error_response_factory(e=e), status=HTTPStatus.NOT_IMPLEMENTED)
            except SmarterExceptionBase as e:
                return JsonResponse(error_response_factory(e=e), status=HTTPStatus.BAD_REQUEST)
            # pylint: disable=W0718
            except Exception as e:
                return JsonResponse(error_response_factory(e=e), status=HTTPStatus.INTERNAL_SERVER_ERROR)

        return wrapper

    def get(self, request):
        """Get method for PluginManifestView."""
        return self.handler(self.broker.get)()

    def post(self, request):
        """Post method for PluginManifestView."""
        return self.handler(self.broker.post)()

    def put(self, request):
        """Put method for PluginManifestView."""
        return self.handler(self.broker.put)()

    def patch(self, request):
        """Patch method for PluginManifestView."""
        return self.handler(self.broker.patch)()

    def delete(self, request):
        """Delete method for PluginManifestView."""
        return self.handler(self.broker.delete)()
