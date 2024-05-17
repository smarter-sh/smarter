# pylint: disable=W0613
"""Smarter API Manifest Abstract Broker class."""

import re
import traceback
import typing
from abc import ABC, abstractmethod
from http import HTTPStatus

import inflect
from django.http import HttpRequest, JsonResponse

from smarter.lib.django.user import UserType
from smarter.lib.manifest.enum import SAMApiVersions
from smarter.lib.manifest.loader import SAMLoader, SAMLoaderError
from smarter.lib.manifest.models import AbstractSAMBase

from .enum import SAMApiVersions
from .exceptions import SAMExceptionBase


if typing.TYPE_CHECKING:
    from smarter.apps.account.models import Account, UserProfile

inflect_engine = inflect.engine()

SUPPORTED_API_VERSIONS = [SAMApiVersions.V1.value]


class SAMBrokerError(SAMExceptionBase):
    """Base class for all SAMBroker errors."""

    @property
    def get_readable_name(self):
        return "Smarter API Manifest Broker Error"


# pylint: disable=too-many-public-methods
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

    class Operations:
        """Common operations for the broker."""

        GET = "get"
        APPLY = "apply"
        DESCRIBE = "describe"
        DELETE = "delete"
        DEPLOY = "deploy"
        LOGS = "logs"

        @classmethod
        def past_tense(cls) -> dict:
            return {
                cls.GET: "gotten",
                cls.APPLY: "applied",
                cls.DESCRIBE: "described",
                cls.DELETE: "deleted",
                cls.DEPLOY: "deployed",
                cls.LOGS: "got logs for",
            }

    _api_version: str = None
    _account: "Account" = None
    _loader: SAMLoader = None
    _manifest: AbstractSAMBase = None
    _name: str = None
    _kind: str = None
    _validated: bool = False

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        account: "Account",
        api_version: str = SAMApiVersions.V1.value,
        name: str = None,
        kind: str = None,
        loader: SAMLoader = None,
        manifest: str = None,
        file_path: str = None,
        url: str = None,
    ):
        self._name = name
        self._account = account
        self._loader = loader
        if api_version not in SUPPORTED_API_VERSIONS:
            raise SAMBrokerError(f"Unsupported apiVersion: {api_version}")
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
        except SAMLoaderError:
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
        if not self._name and self.manifest and self.manifest.metadata and self.manifest.metadata.name:
            self._name = self.manifest.metadata.name
        return self._name

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

    @abstractmethod
    def example_manifest(self, kwargs: dict = None) -> JsonResponse:
        """Returns an example yaml manifest document for the kind of resource."""
        raise NotImplementedError

    def not_implemented_response(self) -> JsonResponse:
        """Return a common not implemented response."""
        data = {"message": f"operation not implemented for {self.kind} resources"}
        return JsonResponse(data=data, status=HTTPStatus.NOT_IMPLEMENTED)

    def not_ready_response(self) -> JsonResponse:
        """Return a common not ready response."""
        data = {"message": f"{self.kind} {self.name} not ready"}
        return JsonResponse(data=data, status=HTTPStatus.BAD_REQUEST)

    def err_response(self, operation: str, e: Exception) -> JsonResponse:
        """Return a common error response."""
        tb_str = "".join(traceback.format_tb(e.__traceback__))
        data = {"message": f"could not {operation} {self.kind} {self.name}", "error": str(e), "stacktrace": tb_str}
        return JsonResponse(data=data, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def not_found_response(self) -> JsonResponse:
        """Return a common not found response."""
        data = {"message": f"{self.kind} {self.name} not found"}
        return JsonResponse(data=data, status=HTTPStatus.NOT_FOUND)

    def success_response(
        self,
        operation: str,
        data: dict,
    ) -> JsonResponse:
        """Return a common success response."""
        operated = self.Operations.past_tense().get(operation, operation)
        if operation == self.Operations.GET:
            kind = inflect_engine.plural(self.kind)
            message = f"{kind} {operated} successfully"
        elif operation == self.Operations.LOGS:
            kind = self.kind
            message = f"{kind} {self.name} successfully retrieved logs"
        else:
            kind = self.kind
            message = f"{kind} {self.name} {operated} successfully"
        operation = self.Operations.past_tense().get(operation, operation)
        retval = {
            "data": data,
            "message": message,
        }
        return JsonResponse(data=retval, status=HTTPStatus.OK, safe=False)

    def camel_to_snake(self, dictionary: dict) -> dict:
        """Converts camelCase dict keys to snake_case."""

        def convert(name: str):
            s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
            return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

        retval = {}
        for key, value in dictionary.items():
            if isinstance(value, dict):
                value = self.camel_to_snake(value)
            new_key = convert(key)
            retval[new_key] = value
        return retval

    def snake_to_camel(self, dictionary: dict) -> dict:
        """Converts snake_case dict keys to camelCase."""

        def convert(name: str):
            components = name.split("_")
            return components[0] + "".join(x.title() for x in components[1:])

        retval = {}
        for key, value in dictionary.items():
            if isinstance(value, dict):
                value = self.snake_to_camel(value)
            new_key = convert(key)
            retval[new_key] = value
        return retval


class BrokerNotImplemented(AbstractBroker):
    """An error class to proxy for a broker class that has not been implemented."""

    # pylint: disable=W0231
    def __init__(self):
        raise NotImplementedError("No broker class has been implemented for this kind of manifest.")
