# pylint: disable=W0613
"""Smarter API Manifest Abstract Broker class."""

import typing
from abc import ABC, abstractmethod
from http import HTTPStatus

from django.http import HttpRequest, JsonResponse

from smarter.common.conf import settings as smarter_settings
from smarter.lib.django.user import UserType
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.models import AbstractSAMBase

from .exceptions import SAMValidationError


if typing.TYPE_CHECKING:
    from smarter.apps.account.models import Account, UserProfile

SUPPORTED_API_VERSIONS = ["smarter.sh/v1"]


class AbstractBroker(ABC):
    """
    Smarter API Manifest Broker abstract base class. This class is responsible
    for:
    - loading, and partially validating and parsing a Smarter Api yaml manifest,
      sufficient to enable us to initialize a Pydantic model.
    - implementing the broker service pattern for the underlying object
    - initializing the corresponding Pydantic models.
    - instantiating the underlying Python object

    AbstractBroker defines the broker pattern that provides the generic services
    for the manifest: get, post, put, delete, patch.
    """

    _api_version: str = None
    _account: "Account" = None
    _loader: SAMLoader = None
    _manifest: AbstractSAMBase = None
    _kind: str = None
    _validated: bool = False

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        api_version: str,
        account: "Account",
        kind: str = None,
        loader: SAMLoader = None,
        manifest: str = None,
        file_path: str = None,
        url: str = None,
    ):
        self._account = account
        self._loader = loader
        if api_version not in SUPPORTED_API_VERSIONS:
            raise SAMValidationError(f"Unsupported apiVersion: {api_version}")
        self._api_version = api_version

        try:
            self._loader = SAMLoader(
                api_version=api_version,
                kind=kind,
                manifest=manifest,
                file_path=file_path,
                url=url,
            )
            if self._loader:
                self._validated = True
        except SAMValidationError:
            pass

        self._kind = kind or self.loader.manifest_kind if self.loader else None

    ###########################################################################
    # Class Instance Properties
    ###########################################################################
    @property
    def is_valid(self) -> bool:
        return self._validated

    @property
    def kind(self) -> str:
        """The kind of manifest."""
        return self._kind

    @property
    def name(self) -> str:
        """The name of the manifest."""
        if self.manifest and self.manifest.metadata and self.manifest.metadata.name:
            return self.manifest.metadata.name
        return None

    @property
    def api_version(self) -> str:
        return self._api_version

    @property
    def loader(self) -> SAMLoader:
        return self._loader

    @property
    def account(self) -> "Account":
        return self._account

    @property
    def user(self) -> "UserType":
        raise NotImplementedError

    @property
    def user_profile(self) -> "UserProfile":
        raise NotImplementedError

    def __str__(self):
        return f"{self.manifest.apiVersion} {self.kind} Broker"

    ###########################################################################
    # Abstract Properties
    ###########################################################################

    @property
    def manifest(self) -> AbstractSAMBase:
        """
        The Pydantic model representing the manifest. This is a reference
        implementation of the abstract property, for documentation purposes
        to illustrate the correct way to initialize a AbstractSAMBase Pydantic model.
        The actual property must be implemented by the concrete broker class.
        """
        if self._manifest:
            return self._manifest
        if self.loader:
            self._manifest = AbstractSAMBase(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=self.loader.manifest_metadata,
                spec=self.loader.manifest_spec,
                status=self.loader.manifest_status,
            )
        return self._manifest

    ###########################################################################
    # Abstract Methods
    ###########################################################################
    @abstractmethod
    def get(
        self, request: HttpRequest = None, name: str = None, all_objects: bool = False, tags: str = None
    ) -> JsonResponse:
        """get information about specified resources."""
        raise NotImplementedError

    @abstractmethod
    def apply(self, request: HttpRequest = None) -> JsonResponse:
        """apply a manifest, which works like a upsert."""
        raise NotImplementedError

    @abstractmethod
    def describe(self, request: HttpRequest = None) -> JsonResponse:
        """print the manifest."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, request: HttpRequest = None) -> JsonResponse:
        """delete a resource."""
        raise NotImplementedError

    @abstractmethod
    def deploy(self, request: HttpRequest = None) -> JsonResponse:
        """deploy a resource."""
        raise NotImplementedError

    @abstractmethod
    def logs(self, request: HttpRequest = None) -> JsonResponse:
        """get logs for a resource."""
        raise NotImplementedError

    def example_manifest(self, request: HttpRequest = None) -> str:
        """Returns an example yaml manifest document for the kind of resource."""
        filename = str(self.kind).lower() + ".yaml"
        data = {"filepath": f"https://{smarter_settings.environment_cdn_domain}/cli/example-manifests/{filename}"}
        return self.success_response(data)

    def not_implemented_response(self) -> JsonResponse:
        """Return a common not implemented response."""
        data = {"smarter": f"operation not implemented for {self.kind} resources"}
        return JsonResponse(data=data, status=HTTPStatus.NOT_IMPLEMENTED)

    def not_ready_response(self) -> JsonResponse:
        """Return a common not ready response."""
        data = {"smarter": f"{self.kind} {self.name} not ready"}
        return JsonResponse(data=data, status=HTTPStatus.BAD_REQUEST)

    def err_response(self, operation: str, e: Exception) -> JsonResponse:
        """Return a common error response."""
        data = {"smarter": f"could not {operation} {self.kind} {self.name}", "error": str(e)}
        return JsonResponse(data=data, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def not_found_response(self) -> JsonResponse:
        """Return a common not found response."""
        data = {"smarter": f"{self.kind} {self.name} not found"}
        return JsonResponse(data=data, status=HTTPStatus.NOT_FOUND)

    def success_response(self, data: dict) -> JsonResponse:
        """Return a common success response."""
        return JsonResponse(data=data, status=HTTPStatus.OK, safe=False)


class BrokerNotImplemented(AbstractBroker):
    """An error class to proxy for a broker class that has not been implemented."""

    # pylint: disable=W0231
    def __init__(self):
        raise NotImplementedError("No broker class has been implemented for this kind of manifest.")
