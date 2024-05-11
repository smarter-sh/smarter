"""Smarter API Manifest Abstract Broker class."""

import typing
from abc import ABC, abstractmethod
from http import HTTPStatus

from django.http import JsonResponse

from smarter.common.conf import settings as smarter_settings
from smarter.lib.django.user import UserType
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.models import AbstractSAMBase

from .exceptions import SAMValidationError


if typing.TYPE_CHECKING:
    from smarter.apps.account.models import Account, UserProfile


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
    _loader: SAMLoader = None
    _manifest: AbstractSAMBase = None
    _kind: str = None
    _validated: bool = False

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        api_version: str,
        account_number: str,
        kind: str = None,
        manifest: str = None,
        file_path: str = None,
        url: str = None,
    ):
        SmarterValidator.validate_account_number(account_number)
        self._api_version = api_version

        try:
            self._loader = SAMLoader(
                api_version=account_number,
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
        raise NotImplementedError

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
    @abstractmethod
    def manifest(self) -> AbstractSAMBase:
        """
        The Pydantic model representing the manifest. This is a reference
        implementation of the abstract property, for documentation purposes
        to illustrate the correct way to initialize a AbstractSAMBase Pydantic model.
        The actual property must be implemented by the concrete broker class.
        """
        if self._manifest:
            return self._manifest
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
    def apply(self) -> JsonResponse:
        """apply a manifest, which works like a upsert."""
        raise NotImplementedError

    @abstractmethod
    def describe(self) -> JsonResponse:
        raise NotImplementedError

    @abstractmethod
    def delete(self) -> JsonResponse:
        raise NotImplementedError

    @abstractmethod
    def deploy(self) -> JsonResponse:
        raise NotImplementedError

    @abstractmethod
    def logs(self) -> JsonResponse:
        raise NotImplementedError

    def example_manifest(self) -> str:
        """Returns an example yaml manifest document for the kind of resource."""
        filename = str(self.kind).lower() + ".yaml"
        data = {"filepath": f"https://{smarter_settings.environment_cdn_domain}/cli/example-manifests/{filename}"}
        return data

    def not_implemented_response(self) -> JsonResponse:
        data = {"smarter": f"operation not implemented for {self.kind} resources"}
        return JsonResponse(data=data, status=HTTPStatus.NOT_IMPLEMENTED)

    def not_ready_response(self) -> JsonResponse:
        data = {"smarter": f"{self.kind} {self.name} not ready"}
        return JsonResponse(data=data, status=HTTPStatus.BAD_REQUEST)

    def err_response(self, operation: str, e: Exception) -> JsonResponse:
        data = {"smarter": f"could not {operation} {self.kind} {self.name}", "error": str(e)}
        return JsonResponse(data=data, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def success_response(self, data: dict) -> JsonResponse:
        return JsonResponse(data=data, status=HTTPStatus.OK)


class BrokerNotImplemented(AbstractBroker):
    """An error class to proxy for a broker class that has not been implemented."""

    # pylint: disable=W0231
    def __init__(self):
        raise NotImplementedError("No broker class has been implemented for this kind of manifest.")
