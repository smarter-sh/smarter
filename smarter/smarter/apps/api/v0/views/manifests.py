# pylint: disable=W0613
"""This module contains the PluginManifestView for the smarter api."""

from http import HTTPStatus
from typing import Dict, Type

from django.http import HttpResponse, JsonResponse

from smarter.apps.api.v0.manifests.broker import SAMBroker
from smarter.apps.api.v0.manifests.enum import SAMKinds
from smarter.apps.api.v0.manifests.exceptions import SAMValidationError
from smarter.apps.api.v0.manifests.loader import SAMLoader
from smarter.apps.plugin.api.v0.manifests.broker import SAMPluginBroker
from smarter.common.exceptions import (
    SmarterBusinessRuleViolation,
    SmarterValueError,
    error_response_factory,
)
from smarter.lib.django.request import SmarterRequestHelper
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

    @property
    def loader(self) -> SAMLoader:
        """Get the SAMLoader instance."""
        return self._loader

    @property
    def broker(self) -> SAMBroker:
        """Get the SAMBroker instance."""
        return self._broker

    def dispatch(self, request, *args, **kwargs):
        """
        The http request body is expected to contain the manifest text
        in yaml format. The manifest text is passed to the SAMLoader that will load,
        and partially validate and parse the manifest. This is then used to
        fully initialize a Pydantic manifest model. The Pydantic manifest
        model will be passed to a SAMBroker for the manifest 'kind', which
        implements the broker service pattern for the underlying object.

        TODO: setup api key authentication
        """

        request_helper = SmarterRequestHelper(request)
        manifest_text = request.body.decode("utf-8")

        # use the loader to retrieve the manifest 'kind'
        try:
            self._loader = SAMLoader(account_number=request_helper.account.account_number, manifest=manifest_text)
        except SAMValidationError as e:
            return JsonResponse(error_response_factory(e=e), status=HTTPStatus.BAD_REQUEST)

        kind = self.loader.manifest_kind
        Broker: SAMBroker = BROKERS.get(kind)
        if Broker is None:
            return JsonResponse(
                {"error": f"Unsupported manifest kind: {kind}"},
                status=HTTPStatus.BAD_REQUEST,
            )

        try:
            self._broker = Broker(account_number=request_helper.account.account_number, manifest=manifest_text)
        except (SAMValidationError, SmarterBusinessRuleViolation, SmarterValueError) as e:
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
            except (SAMValidationError, SmarterBusinessRuleViolation, SmarterValueError) as e:
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
