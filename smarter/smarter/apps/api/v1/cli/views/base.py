"""Smarter API command-line interface Base class API view"""

import json
import logging
from http import HTTPStatus
from typing import Type

import yaml
from django.http import JsonResponse
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.utils import user_profile_for_user
from smarter.apps.api.v1.cli.brokers import BROKERS
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.api.v1.manifests.version import SMARTER_API_VERSION
from smarter.common.exceptions import SmarterExceptionBase, error_response_factory
from smarter.lib.drf.token_authentication import SmarterTokenAuthentication
from smarter.lib.manifest.broker import AbstractBroker
from smarter.lib.manifest.exceptions import SAMBadRequestError
from smarter.lib.manifest.loader import SAMLoader


logger = logging.getLogger(__name__)


class APIV1CLIViewError(SmarterExceptionBase):
    """Base class for all APIV1CLIView errors."""

    @property
    def get_readable_name(self):
        return "Smarter api v1 command-line interface error"


# pylint: disable=too-many-instance-attributes
class CliBaseApiView(APIView, AccountMixin):
    """
    Smarter API command-line interface Base class API view. Handles
    common tasks for all /api/v1/cli views:
    - Authenticates the request using either knox TokenAuthentication
      or Django SessionAuthentication.
    - Initializes the SAMLoader and AbstractBroker instances.
    - Resolves the manifest kind and broker for the yaml manifest document.
    - Sets the user profile for the request.
    """

    authentication_classes = (SmarterTokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    _loader: SAMLoader = None
    _broker: AbstractBroker = None
    _manifest_data: json = None
    _manifest_kind: str = None
    _manifest_name: str = None
    _manifest_load_failed: bool = False
    _BrokerClass: Type[AbstractBroker] = None

    @property
    def loader(self) -> SAMLoader:
        """
        Get the SAMLoader instance. a SAMLoader instance is used to load
        raw manifest text into a Pydantic model. It performs cursory validations
        such as validating the file format, and identifying required dict key values
        such as the api version, the manifest kind and its name.
        """
        if not self._loader and self.manifest_data and not self._manifest_load_failed:
            try:
                self._loader = SAMLoader(
                    api_version=SMARTER_API_VERSION,
                    kind=self.manifest_kind,
                    manifest=self.manifest_data,
                )
                if not self._loader:
                    print("loader() -  exception: SAMValidationError")
                    raise APIV1CLIViewError("")
            except APIV1CLIViewError as e:
                print("loader() -  exception: SAMValidationError", e)
                # not all endpoints require a manifest, so we
                # should fail gracefully if the manifest is not provided.
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
                raise APIV1CLIViewError(f"Could not find broker for {self.manifest_kind} manifest.")
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
                name=self.manifest_name,
                kind=self.manifest_kind,
                account=self.user_profile.account,
                loader=self.loader,
                manifest=self.loader.yaml_data if self.loader else None,
            )
            if not self._broker:
                raise APIV1CLIViewError("Could not load manifest.")

        return self._broker

    @property
    def manifest_data(self) -> json:
        return self._manifest_data

    @property
    def manifest_name(self) -> str:
        if not self._manifest_name and self.manifest_data:
            self._manifest_name = self.manifest_data.get("metadata", {}).get("name", None)
        if not self._manifest_kind and self.loader:
            self._manifest_kind = self.loader.manifest_metadata.get("name") if self.loader else None
        return self._manifest_name

    @property
    def manifest_kind(self) -> str:
        if not self._manifest_kind and self.manifest_data:
            self._manifest_kind = str(self.manifest_data.get("kind", None))
        if not self._manifest_kind and self.loader:
            self._manifest_kind = str(self.loader.manifest_kind) if self.loader else None
        return self._manifest_kind.lower() if self._manifest_kind else None

    # pylint: disable=too-many-return-statements,too-many-branches
    def dispatch(self, request, *args, **kwargs):
        """
        The http request body is expected to contain the manifest text
        in yaml format. The manifest text is passed to the SAMLoader that will load,
        and partially validate and parse the manifest. This is then used to
        fully initialize a Pydantic manifest model. The Pydantic manifest
        model will be passed to a AbstractBroker for the manifest 'kind', which
        implements the broker service pattern for the underlying object.
        """
        logger.info("dispatch() - kwargs: %s", kwargs)
        logger.info("dispatch() - request.GET: %s", request.GET)
        # TO DO: This is a temporary fix to mitigate a configuration issue
        # where DRF is not properly authenticating the request. This is a
        # temporary fix until we can properly configure the DRF authentication
        if not hasattr(request, "auth"):
            logger.info("authentication_classes: %s", self.authentication_classes)
            logger.info("permission_classes: %s", self.permission_classes)
            logger.warning(
                "No authentication scheme detected in the request object. forcing authentication via SmarterTokenAuthentication."
            )
            request.auth = SmarterTokenAuthentication()
            try:
                user, _ = request.auth.authenticate(request)
                request.user = user
            except AuthenticationFailed:
                try:
                    raise APIV1CLIViewError("Authentication failed.") from None
                except APIV1CLIViewError as e:
                    return JsonResponse(error_response_factory(e=e), status=HTTPStatus.FORBIDDEN)
        if not request.user.is_authenticated:
            try:
                raise APIV1CLIViewError("Authentication failed.")
            except APIV1CLIViewError as e:
                return JsonResponse(error_response_factory(e=e), status=HTTPStatus.FORBIDDEN)

        user_agent = request.headers.get("User-Agent", "")
        if "Go-http-client" not in user_agent:
            logger.warning("The User-Agent is not a Go lang application: %s", user_agent)

        self._manifest_name = kwargs.get("name", None)
        kind = kwargs.get("kind", None)
        if kind:
            self._manifest_kind = kind
            if self.manifest_kind.endswith("s"):
                self._manifest_kind = self.manifest_kind[:-1]
            if self.manifest_kind:
                # Validate the manifest kind: plugin, plugins, user, users, chatbot, chatbots, etc.
                if str(self.manifest_kind).lower() not in SAMKinds.all_slugs():
                    print(f"Unsupported manifest kind: {self.manifest_kind}. should be one of {SAMKinds.all_slugs()}")
                    return JsonResponse(
                        error_response_factory(
                            e=SAMBadRequestError(f"Unsupported manifest kind: {self.manifest_kind}")
                        ),
                        status=HTTPStatus.BAD_REQUEST,
                    )

        # Manifest parsing and broker instantiation are lazy implementations.
        # So for now, we'll only set the private class variable _manifest_data
        # from the request body, and then we'll leave it to the child views to
        # decide if/when to actually parse the manifest and instantiate the broker.
        try:
            data = request.body.decode("utf-8")
            self._manifest_data = json.loads(data)
        except json.JSONDecodeError:
            try:
                self._manifest_data = yaml.safe_load(data)
            except yaml.YAMLError as e:
                try:
                    raise APIV1CLIViewError("Could not parse manifest. Valid formats: yaml, json.") from e
                except APIV1CLIViewError as ex:
                    return JsonResponse(error_response_factory(e=ex), status=HTTPStatus.BAD_REQUEST)
        try:
            self._user_profile = user_profile_for_user(user=request.user)
            self._account = self._user_profile.account
            self._user = self._user_profile.user
            if not self._user_profile:
                raise APIV1CLIViewError("Could not find account for user.")
        except SmarterExceptionBase as e:
            return JsonResponse(error_response_factory(e=e), status=HTTPStatus.FORBIDDEN)

        # generic exception handler that simply ensures that in all cases
        # the response is a JsonResponse with a status code.
        try:
            return super().dispatch(request, *args, **{**request.GET.dict(), **kwargs})
        # pylint: disable=broad-except
        except Exception as e:
            return JsonResponse(error_response_factory(e=e), status=HTTPStatus.INTERNAL_SERVER_ERROR)
