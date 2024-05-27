# pylint: disable=W0613
"""Smarter API Manifest Abstract Broker class."""

import re
import typing
from abc import ABC, abstractmethod
from http import HTTPStatus

import inflect
from django.http import HttpRequest
from rest_framework.serializers import ModelSerializer

from smarter.common.api import SmarterApiVersions
from smarter.lib.journal.enum import (
    SmarterJournalApiResponseErrorKeys,
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
    SmarterJournalThings,
)
from smarter.lib.journal.http import (
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
)
from smarter.lib.manifest.loader import SAMLoader, SAMLoaderError
from smarter.lib.manifest.models import AbstractSAMBase

from .exceptions import SAMExceptionBase


if typing.TYPE_CHECKING:
    from smarter.apps.account.models import Account

inflect_engine = inflect.engine()

SUPPORTED_API_VERSIONS = [SmarterApiVersions.V1.value]


class SAMBrokerError(SAMExceptionBase):
    """Base class for all SAMBroker errors."""

    thing: SmarterJournalThings = None
    command: SmarterJournalCliCommands = None

    def __init__(self, message: str, thing: SmarterJournalThings = None, command: SmarterJournalCliCommands = None):
        self.thing = thing
        self.command = command
        super().__init__(message)

    @property
    def get_readable_name(self):
        return "Smarter API Manifest Broker Error"


class SAMBrokerReadOnlyError(SAMBrokerError):
    """Error for read-only broker operations."""

    @property
    def get_readable_name(self):
        return "Smarter API Manifest Broker Read-Only Error"


class SAMBrokerErrorNotImplemented(SAMBrokerError):
    """Base class for all SAMBroker errors."""

    @property
    def get_readable_name(self):
        return "Smarter API Manifest Broker Not Implemented Error"


class SAMBrokerErrorNotReady(SAMBrokerError):
    """Error for broker operations on resources that are not ready."""

    @property
    def get_readable_name(self):
        return "Smarter API Manifest Broker Not Ready Error"


class SAMBrokerErrorNotFound(SAMBrokerError):
    """Error for broker operations on resources that are not found."""

    @property
    def get_readable_name(self):
        return "Smarter API Manifest Broker Not Found Error"


# pylint: disable=too-many-public-methods,too-many-instance-attributes
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

    _request: HttpRequest = None
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
        request: HttpRequest,
        account: "Account",
        api_version: str = SmarterApiVersions.V1.value,
        name: str = None,
        kind: str = None,
        loader: SAMLoader = None,
        manifest: str = None,
        file_path: str = None,
        url: str = None,
    ):
        self._request = request
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
    def request(self) -> HttpRequest:
        return self._request

    @property
    def is_valid(self) -> bool:
        return self._validated

    @property
    def thing(self) -> SmarterJournalThings:
        return SmarterJournalThings(self.kind)

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

    def __str__(self):
        return f"{self.manifest.apiVersion} {self.kind} Broker"

    ###########################################################################
    # Abstract Properties
    ###########################################################################
    @property
    def model_class(self):
        raise NotImplementedError

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
    def get(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        """get information about specified resources."""
        raise NotImplementedError

    def apply(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        """apply a manifest, which works like a upsert."""
        if self.manifest.status:
            raise SAMBrokerReadOnlyError("status is a read-only manifest field for")

    @abstractmethod
    def describe(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        """print the manifest."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        """delete a resource."""
        raise NotImplementedError

    @abstractmethod
    def deploy(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        """deploy a resource."""
        raise NotImplementedError

    @abstractmethod
    def undeploy(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        """undeploy a resource."""
        raise NotImplementedError

    @abstractmethod
    def logs(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        """get logs for a resource."""
        raise NotImplementedError

    @abstractmethod
    def example_manifest(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        """Returns an example yaml manifest document for the kind of resource."""
        raise NotImplementedError

    # pylint: disable=W0212
    def get_model_titles(self, serializer: ModelSerializer) -> list[dict[str, str]]:
        fields_and_types = [
            {"name": field_name, "type": type(field).__name__} for field_name, field in serializer.fields.items()
        ]
        return fields_and_types

    ###########################################################################
    # http json response helpers
    ###########################################################################
    def _retval(self, data: dict = None, error: dict = None, message: str = None) -> dict[str, typing.Any]:
        retval = {}
        if data:
            retval[SmarterJournalApiResponseKeys.DATA] = data
        if error:
            retval[SmarterJournalApiResponseKeys.ERROR] = error
        if message:
            retval[SmarterJournalApiResponseKeys.MESSAGE] = message

        return retval

    def json_response_ok(self, command: SmarterJournalCliCommands, data: dict = None) -> SmarterJournaledJsonResponse:
        """Return a common success response."""
        data = data or {}
        operated = SmarterJournalCliCommands.past_tense().get(command, command)
        if command == SmarterJournalCliCommands.GET:
            kind = inflect_engine.plural(self.kind)
            message = f"{kind} {operated} successfully"
        elif command == SmarterJournalCliCommands.LOGS:
            kind = self.kind
            message = f"{kind} {self.name} successfully retrieved logs"
        elif command == SmarterJournalCliCommands.MANIFEST_EXAMPLE:
            kind = self.kind
            message = f"{kind} example manifest successfully generated"
        else:
            kind = self.kind
            message = f"{kind} {self.name} {operated} successfully"
        retval = self._retval(data=data, message=message)
        return SmarterJournaledJsonResponse(
            request=self.request, thing=self.thing, command=command, data=retval, status=HTTPStatus.OK, safe=False
        )

    def json_response_err_readonly(self, command: SmarterJournalCliCommands) -> SmarterJournaledJsonResponse:
        """Return a common read-only response."""
        message = f"{self.kind} {self.name} is read-only"
        error = {
            SmarterJournalApiResponseErrorKeys.ERROR_CLASS: SAMBrokerReadOnlyError.__name__,
            SmarterJournalApiResponseErrorKeys.STACK_TRACE: None,
            SmarterJournalApiResponseErrorKeys.DESCRIPTION: message,
            SmarterJournalApiResponseErrorKeys.STATUS: "",
            SmarterJournalApiResponseErrorKeys.ARGS: None,
            SmarterJournalApiResponseErrorKeys.CAUSE: None,
            SmarterJournalApiResponseErrorKeys.CONTEXT: None,
        }
        retval = self._retval(error=error, message=message)
        return SmarterJournaledJsonResponse(
            request=self.request, thing=self.thing, command=command, data=retval, status=HTTPStatus.METHOD_NOT_ALLOWED
        )

    def json_response_err_notimplemented(self, command: SmarterJournalCliCommands) -> SmarterJournaledJsonResponse:
        """Return a common not implemented response."""
        message = f"command not implemented for {self.kind} resources"
        error = {
            SmarterJournalApiResponseErrorKeys.ERROR_CLASS: SAMBrokerErrorNotImplemented.__name__,
            SmarterJournalApiResponseErrorKeys.STACK_TRACE: None,
            SmarterJournalApiResponseErrorKeys.DESCRIPTION: message,
            SmarterJournalApiResponseErrorKeys.STATUS: "",
            SmarterJournalApiResponseErrorKeys.ARGS: None,
            SmarterJournalApiResponseErrorKeys.CAUSE: None,
            SmarterJournalApiResponseErrorKeys.CONTEXT: None,
        }
        retval = self._retval(error=error, message=message)
        return SmarterJournaledJsonResponse(
            request=self.request, thing=self.thing, command=command, data=retval, status=HTTPStatus.NOT_IMPLEMENTED
        )

    def json_response_err_notready(self, command: SmarterJournalCliCommands) -> SmarterJournaledJsonResponse:
        """Return a common not ready response."""
        message = f"{self.kind} {self.name} not ready"
        error = {
            SmarterJournalApiResponseErrorKeys.ERROR_CLASS: SAMBrokerErrorNotReady.__name__,
            SmarterJournalApiResponseErrorKeys.STACK_TRACE: None,
            SmarterJournalApiResponseErrorKeys.DESCRIPTION: message,
            SmarterJournalApiResponseErrorKeys.STATUS: "",
            SmarterJournalApiResponseErrorKeys.ARGS: None,
            SmarterJournalApiResponseErrorKeys.CAUSE: None,
            SmarterJournalApiResponseErrorKeys.CONTEXT: None,
        }
        retval = self._retval(error=error, message=message)
        return SmarterJournaledJsonResponse(
            request=self.request, thing=self.thing, command=command, data=retval, status=HTTPStatus.BAD_REQUEST
        )

    def json_response_err_notfound(
        self, command: SmarterJournalCliCommands, message: str = None
    ) -> SmarterJournaledJsonResponse:
        """Return a common not found response."""
        message = message or f"{self.kind} {self.name} not found"
        error = {
            SmarterJournalApiResponseErrorKeys.ERROR_CLASS: SAMBrokerErrorNotFound.__name__,
            SmarterJournalApiResponseErrorKeys.STACK_TRACE: None,
            SmarterJournalApiResponseErrorKeys.DESCRIPTION: message,
            SmarterJournalApiResponseErrorKeys.STATUS: "",
            SmarterJournalApiResponseErrorKeys.ARGS: None,
            SmarterJournalApiResponseErrorKeys.CAUSE: None,
            SmarterJournalApiResponseErrorKeys.CONTEXT: None,
        }
        retval = self._retval(error=error, message=message)
        return SmarterJournaledJsonResponse(
            request=self.request, thing=self.thing, command=command, data=retval, status=HTTPStatus.NOT_FOUND
        )

    def json_response_err(self, command: SmarterJournalCliCommands, e: Exception) -> SmarterJournaledJsonResponse:
        """
        Return a structured error response that can be unpacked and rendered
        by the cli in a variety of formats.
        """
        return SmarterJournaledJsonErrorResponse(
            request=self.request, thing=self.thing, command=command, e=e, status=HTTPStatus.INTERNAL_SERVER_ERROR
        )

    ###########################################################################
    # data transformation helpers
    ###########################################################################
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
