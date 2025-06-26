# pylint: disable=W0613
"""Smarter API Manifest Abstract Broker class."""

import logging
import re
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from http import HTTPStatus
from typing import Any, Optional, Type, Union
from urllib.parse import parse_qs, urlparse

import inflect
from django.http import HttpRequest, QueryDict
from requests import PreparedRequest
from rest_framework.serializers import ModelSerializer

from smarter.apps.account.models import Secret, UserProfile
from smarter.common.api import SmarterApiVersions
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django.model_helpers import TimestampedModel
from smarter.lib.django.request import SmarterRequestMixin
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
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys
from smarter.lib.manifest.loader import SAMLoader, SAMLoaderError
from smarter.lib.manifest.models import (
    AbstractSAMBase,
    AbstractSAMMetadataBase,
    AbstractSAMSpecBase,
    AbstractSAMStatusBase,
)

from .exceptions import SAMExceptionBase


inflect_engine = inflect.engine()

SUPPORTED_API_VERSIONS = [SmarterApiVersions.V1]

logger = logging.getLogger(__name__)


class SAMBrokerError(SAMExceptionBase):
    """Base class for all SAMBroker errors."""

    thing: Optional[Union[SmarterJournalThings, str]] = None
    command: Optional[SmarterJournalCliCommands] = None
    stack_trace: Optional[str] = None

    def __init__(
        self,
        message: Optional[str] = None,
        thing: Optional[Union[SmarterJournalThings, str]] = None,
        command: Optional[SmarterJournalCliCommands] = None,
        stack_trace: Optional[str] = None,
    ):
        self.thing = thing
        self.command = command
        self.stack_trace = stack_trace
        super().__init__(message or "")

    @property
    def get_formatted_err_message(self):
        msg = f"Smarter API {self.thing} manifest broker: {self.command}() unidentified error."
        if self.message:
            msg += "  " + self.message
        return msg


class SAMBrokerReadOnlyError(SAMBrokerError):
    """Error for read-only broker operations."""

    @property
    def get_formatted_err_message(self):
        msg = f"Smarter API {self.thing} manifest broker: {self.command}() read-only error."
        if self.message:
            msg += "  " + self.message
        return msg


class SAMBrokerErrorNotImplemented(SAMBrokerError):
    """Base class for all SAMBroker errors."""

    @property
    def get_formatted_err_message(self):
        msg = f"Smarter API {self.thing} manifest broker: {self.command}() not implemented error."
        if self.message:
            msg += "  " + self.message
        return msg


class SAMBrokerErrorNotReady(SAMBrokerError):
    """Error for broker operations on resources that are not ready."""

    @property
    def get_formatted_err_message(self):
        msg = f"Smarter API {self.thing} manifest broker: {self.command}() not ready error."
        if self.message:
            msg += "  " + self.message
        return msg


class SAMBrokerErrorNotFound(SAMBrokerError):
    """Error for broker operations on resources that are not found."""

    @property
    def get_formatted_err_message(self):
        msg = f"Smarter API {self.thing} manifest broker: {self.command}() not found error."
        if self.message:
            msg += "  " + self.message
        return msg


class AbstractBroker(ABC, SmarterRequestMixin):
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

    _api_version: Optional[str] = None
    _loader: Optional[SAMLoader] = None
    _manifest: Optional[AbstractSAMBase] = None
    _pydantic_model: Type[AbstractSAMBase] = AbstractSAMBase
    _name: Optional[str]
    _kind: Optional[str]
    _validated: bool = False
    _thing: Optional[SmarterJournalThings] = None
    _created: bool = False

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ):
        SmarterRequestMixin.__init__(self, request, *args, **kwargs)
        logger.info(
            "AbstractBroker.__init__() initializing request: %s, args: %s, kwargs: %s", self.request, args, kwargs
        )

        self._name = kwargs.get("name")
        self._kind = kwargs.get("kind")
        self._loader = kwargs.get("loader")
        api_version: Optional[str] = kwargs.get("api_version", SmarterApiVersions.V1)
        manifest: Optional[str] = kwargs.get("manifest")
        file_path: Optional[str] = kwargs.get("file_path")
        url: Optional[str] = kwargs.get("url")

        if api_version not in SUPPORTED_API_VERSIONS:
            raise SAMBrokerError(
                message=f"Unsupported apiVersion: {api_version}",
                thing=SmarterJournalThings.ACCOUNT,
            )
        self._api_version = api_version

        try:
            self._loader = SAMLoader(
                api_version=api_version,
                kind=self.kind,
                manifest=manifest,
                file_path=file_path,
                url=url,
            )
            if self._loader:
                self._validated = True
        except SAMLoaderError as e:
            logger.error("%s.__init__() failed to initialize loader: %s", self.formatted_class_name, str(e))

        if self.user:
            logger.info("%s.__init__() received user: %s", self.formatted_class_name, self.user_profile)

        if self._name:
            logger.info("%s.__init__() set name to %s", self.formatted_class_name, self._name)

        if self._loader:
            logger.info("%s.__init__() received a %s loader", self.formatted_class_name, self._loader.manifest_kind)
            self._validated = True
            logger.info(
                "%s.__init__() loader initialized with manifest kind: %s",
                self.formatted_class_name,
                self._loader.manifest_kind,
            )

        self._kind = self._kind or self.loader.manifest_kind if self.loader else None
        self._created = False
        logger.info(
            "AbstractBroker.__init__() finished initializing %s with api_version: %s, user: %s, name: %s",
            self.kind,
            self.api_version,
            self.user_profile,
            self.name,
        )

    ###########################################################################
    # Class Instance Properties
    ###########################################################################
    @property
    def formatted_class_name(self) -> str:
        """
        Returns the formatted class name for logging purposes.
        This is used to provide a more readable class name in logs.
        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.AbstractBroker()"

    @property
    def request(self) -> HttpRequest:
        """Return the request object."""
        return self.smarter_request

    @property
    def params(self) -> Optional[QueryDict]:
        """
        Return the query parameters from the url of the request. there are two
        scenarios to consider:
        1. the request is a Django HttpRequest object (the expected case)
        2. the request is a Python PreparedRequest object (the edge case)
        """
        if isinstance(self.request, PreparedRequest):
            query = urlparse(self.request.url).query
            if not query:
                return QueryDict("", mutable=True)
            if isinstance(query, (bytes, bytearray, memoryview)):
                query = query.decode("utf-8") if not isinstance(query, memoryview) else query.tobytes().decode("utf-8")
            query_params = parse_qs(query)
            flat_params = {k: v[0] for k, v in query_params.items()}
            qd = QueryDict("", mutable=True)
            qd.update(flat_params)
            return qd
        return self.request.GET if self.request else QueryDict("", mutable=True)

    @property
    def uri(self) -> Optional[str]:
        """Return the full uri of the request."""
        if not self.request:
            return None

        scheme = self.request.scheme
        host = self.request.get_host()
        path = self.request.path
        params = self.request.GET.urlencode()

        url = f"{scheme}://{host}{path}"
        if params:
            url += f"?{params}"

        return url

    @property
    def created(self) -> bool:
        """Return True if the broker was created successfully."""
        return self._created

    @property
    def is_valid(self) -> bool:
        return self._validated

    @property
    def thing(self) -> SmarterJournalThings:
        if not self._thing:
            self._thing = SmarterJournalThings(self.kind)
        return self._thing

    @property
    def kind(self) -> Optional[str]:
        """The kind of manifest."""
        return self._kind

    @property
    def name(self) -> Optional[str]:
        """The name of the manifest."""
        if self._name:
            return self._name
        if not self._name and self.manifest and self.manifest.metadata and self.manifest.metadata.name:
            # assign from the manifest metadata, if we have it
            self._name = self.manifest.metadata.name
            logger.info("%s.name() set name to %s from manifest metadata", self.formatted_class_name, self._name)
        if isinstance(self.params, QueryDict):
            name_param = self.params.get("name", None)
            if name_param:
                self._name = name_param
                logger.info("%s.__init__() set name to %s from name url param", self.formatted_class_name, self._name)

        return self._name

    @property
    def api_version(self) -> Optional[str]:
        return self._api_version

    @property
    def loader(self) -> Optional[SAMLoader]:
        if self._loader and self._loader.ready:
            return self._loader

    def __str__(self):
        return f"{self.manifest.apiVersion if self.manifest else "Unknown Version"} {self.kind} Broker"

    ###########################################################################
    # Abstract Properties
    ###########################################################################
    @property
    def serializer(self) -> Optional[ModelSerializer]:
        """Return the serializer for the broker."""
        raise SAMBrokerErrorNotImplemented(message="", thing=self.thing, command=None)

    @property
    def model_class(self) -> Type[TimestampedModel]:
        """Return the Django ORM model class for the broker."""
        raise SAMBrokerErrorNotImplemented(message="", thing=self.thing, command=None)

    @property
    def pydantic_model(self) -> Type[AbstractSAMBase]:
        """Return the Pydantic model for the broker."""
        return self._pydantic_model

    @property
    def manifest(self) -> Optional[AbstractSAMBase]:
        """
        The Pydantic model representing the manifest. This is a reference
        implementation of the abstract property, for documentation purposes
        to illustrate the correct way to initialize a AbstractSAMBase Pydantic model.
        The actual property must be implemented by the concrete broker class.
        """
        if self._manifest:
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = AbstractSAMBase(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=AbstractSAMMetadataBase(**self.loader.manifest_metadata),
                spec=AbstractSAMSpecBase(**self.loader.manifest_spec),
                status=AbstractSAMStatusBase(**self.loader.manifest_status),
            )
        return self._manifest

    ###########################################################################
    # Abstract Methods
    ###########################################################################
    # mcdaniel: there's a reason why this is not an abstract method, but i forget why.
    def apply(self, request: HttpRequest, *args, **kwargs) -> Optional[SmarterJournaledJsonResponse]:
        """
        apply a manifest, which works like a upsert.
        metadata:
            description: new description
            name: test71d12b8212b628df
            version: 1.0.0

        """
        logger.info("AbstractBroker.apply() called %s with args: %s, kwargs: %s", request, args, kwargs)

    @abstractmethod
    def chat(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """chat with the broker."""
        raise SAMBrokerErrorNotImplemented(
            message="chat() not implemented", thing=self.thing, command=SmarterJournalCliCommands.CHAT
        )

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        raise SAMBrokerErrorNotImplemented(
            message="chat() not implemented", thing=self.thing, command=SmarterJournalCliCommands.DESCRIBE
        )

    @abstractmethod
    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """delete a resource."""
        raise SAMBrokerErrorNotImplemented(
            message="delete() not implemented", thing=self.thing, command=SmarterJournalCliCommands.DELETE
        )

    @abstractmethod
    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """deploy a resource."""
        raise SAMBrokerErrorNotImplemented(
            message="deploy() not implemented", thing=self.thing, command=SmarterJournalCliCommands.DEPLOY
        )

    @abstractmethod
    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Returns an example yaml manifest document for the kind of resource."""
        raise SAMBrokerErrorNotImplemented(
            message="example_manifest() not implemented",
            thing=self.thing,
            command=SmarterJournalCliCommands.MANIFEST_EXAMPLE,
        )

    @abstractmethod
    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """get information about specified resources."""
        raise SAMBrokerErrorNotImplemented(
            message="get() not implemented", thing=self.thing, command=SmarterJournalCliCommands.GET
        )

    @abstractmethod
    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """get logs for a resource."""
        raise SAMBrokerErrorNotImplemented(
            message="logs() not implemented", thing=self.thing, command=SmarterJournalCliCommands.LOGS
        )

    @abstractmethod
    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """undeploy a resource."""
        raise SAMBrokerErrorNotImplemented(
            message="undeploy() not implemented", thing=self.thing, command=SmarterJournalCliCommands.UNDEPLOY
        )

    def schema(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return the published JSON schema for the Pydantic model."""
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)

        model = self.pydantic_model
        data = model.model_json_schema()

        return self.json_response_ok(command=command, data=data)

    ###########################################################################
    # Smarter object helpers
    ###########################################################################
    def get_or_create_secret(
        self,
        user_profile: UserProfile,
        name: str,
        value: Optional[str] = None,
        description: Optional[str] = None,
        expiration: Optional[datetime] = None,
    ) -> Secret:
        """
        Get or create a Smarter Secret in the database. This is used to store
        secrets that are passed in the manifest.
        """
        secret: Optional[Secret] = None
        try:
            secret = Secret.objects.get(name=name, user_profile=user_profile)
        except Secret.DoesNotExist as e:

            if not value:
                raise SAMBrokerError(
                    message=f"Secret {name} not found and no value was provided provided",
                    thing=self.thing,
                    command=SmarterJournalCliCommands.GET,
                ) from e

            if not user_profile:
                raise SAMBrokerError(
                    message=f"Secret {name} not found and no user_profile was provided provided",
                    thing=self.thing,
                    command=SmarterJournalCliCommands.GET,
                ) from e

            if not description:
                description = f"[auto generated] Secret {name} for {user_profile.user.username}"

            encrypted_value = Secret.encrypt(value)

            secret = Secret.objects.create(
                user_profile=user_profile,
                name=name,
                description=description,
                encrypted_value=encrypted_value,
                expires_at=expiration,
            )

        return secret

    ###########################################################################
    # http json response helpers
    ###########################################################################
    def _retval(
        self, data: Optional[dict] = None, error: Optional[dict] = None, message: Optional[str] = None
    ) -> dict[str, Any]:
        retval = {}
        if data:
            retval[SmarterJournalApiResponseKeys.DATA] = data
        if error:
            retval[SmarterJournalApiResponseKeys.ERROR] = error
        if message:
            retval[SmarterJournalApiResponseKeys.MESSAGE] = message

        return retval

    def json_response_ok(
        self, command: SmarterJournalCliCommands, data: Optional[dict] = None, message: Optional[str] = None
    ) -> SmarterJournaledJsonResponse:
        """Return a common success response."""
        data = data or {}

        operated = SmarterJournalCliCommands.past_tense().get(str(command), command)

        if command == SmarterJournalCliCommands.GET:
            kind = inflect_engine.plural(self.kind)  # type: ignore
            message = message or f"{kind} {operated} successfully"
        elif command == SmarterJournalCliCommands.LOGS:
            kind = self.kind
            message = message or f"{kind} {self.name} successfully retrieved logs"
        elif command == SmarterJournalCliCommands.MANIFEST_EXAMPLE:
            kind = self.kind
            message = message or f"{kind} example manifest successfully generated"
        else:
            kind = self.kind
            message = message or f"{kind} {self.name} {operated} successfully"
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
        self, command: SmarterJournalCliCommands, message: Optional[str] = None
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
        stack_trace = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        return SmarterJournaledJsonErrorResponse(
            request=self.request,
            thing=self.thing,
            command=command,
            e=e,
            stack_trace=stack_trace,
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    ###########################################################################
    # data transformation helpers
    ###########################################################################
    def set_and_verify_name_param(self, *args, command: Optional[SmarterJournalCliCommands] = None, **kwargs):
        """
        Set self.name from the 'name' query string param and then verify that it
        was actually passed.
        """
        self._name = kwargs.get("name", None) or self._name
        if not self.manifest and not self.name:
            raise SAMBrokerErrorNotReady(
                f"If a manifest is not provided then the query param 'name' should be passed to identify the {self.kind}. Received {self.uri}",
                thing=self.kind,
                command=command,
            )

    # pylint: disable=W0212
    def get_model_titles(self, serializer: ModelSerializer) -> Optional[list[dict[str, str]]]:
        """
        For tabular output from get() implementations. Returns a list of field names and types
        from the Django model serializer.
        """
        fields_and_types: list[dict[str, str]] = []
        for field_name, field in serializer.fields.items():
            item = self.snake_to_camel({"name": field_name, "type": type(field).__name__}, convert_values=True)
            if isinstance(item, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in item.items()):
                fields_and_types.append(item)
        return fields_and_types

    def camel_to_snake(self, data: Union[str, dict, list]) -> Optional[Union[str, dict, list]]:
        """Converts camelCase dict keys to snake_case."""

        def convert(name: str):
            s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
            return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

        if isinstance(data, str):
            return convert(data)
        if isinstance(data, list):
            return [self.camel_to_snake(item) for item in data]
        if not isinstance(data, dict):
            raise SmarterValueError(f"Expected data to be a dict or list, got: {type(data)}")
        dictionary: dict = data if isinstance(data, dict) else {}
        retval = {}
        for key, value in dictionary.items():
            if isinstance(value, dict):
                value = self.camel_to_snake(value)
            new_key = convert(key)
            retval[new_key] = value
        return retval

    def snake_to_camel(
        self, data: Union[str, dict, list], convert_values: bool = False
    ) -> Optional[Union[str, dict, list]]:
        """Converts snake_case dict keys to camelCase."""

        def convert(name: str) -> str:
            components = name.split("_")
            return components[0] + "".join(x.title() for x in components[1:])

        if isinstance(data, str):
            return convert(data)

        if isinstance(data, list):
            return [self.snake_to_camel(item, convert_values=convert_values) for item in data]

        if not isinstance(data, dict):
            raise SmarterValueError(f"Expected data to be a dict or list, got: {type(data)}")

        dictionary: dict = data if isinstance(data, dict) else {}
        retval = {}
        for key, value in dictionary.items():
            if isinstance(value, dict):
                value = self.snake_to_camel(data=value, convert_values=convert_values)
            new_key = convert(key)
            if convert_values:
                new_value = convert(value) if isinstance(value, str) else value
            else:
                new_value = value
            retval[new_key] = new_value
        return retval

    def clean_cli_param(self, param, param_name: str = "unknown", url: Optional[str] = None) -> Optional[str]:
        """
        - Remove any leading or trailing whitespace from the param.
        - Ensure that the param is a string.
        - Return the cleaned param.
        """
        class_name = self.__class__.__name__ + "().clean_cli_param()"
        class_name = formatted_text(class_name)
        retval = param.strip() if isinstance(param, str) else param

        if isinstance(param, str):
            param = param.strip()
            if not param:
                logger.warning(
                    "%s param <%s> is an empty string, setting to None for url: %s", class_name, param_name, url
                )
                retval = None
        else:
            logger.warning(
                "%s param: <%s>. Expected str but got type: %s (%s) for url: %s",
                class_name,
                param_name,
                type(param),
                param,
                url,
            )
            if isinstance(param, list):
                retval = param[0]
                logger.warning(
                    "%s set param <%s> to first element of list: %s for url: %s", class_name, param_name, param, url
                )

        return retval


# pylint: disable=W0246
class BrokerNotImplemented(AbstractBroker):
    """An error class to proxy for a broker class that has not been implemented."""

    # pylint: disable=W0231,R0913
    def __init__(
        self,
        request=None,
        api_version=None,
        account=None,
        name=None,
        kind=None,
        loader=None,
        manifest=None,
        file_path=None,
        url=None,
    ):
        raise SAMBrokerErrorNotImplemented(
            message="No broker class has been implemented for this kind of manifest.",
            thing=None,
            command=None,
        )

    def chat(self, request, kwargs):
        super().chat(request, kwargs)

    def delete(self, request, kwargs):
        super().delete(request, kwargs)

    def deploy(self, request, kwargs):
        super().deploy(request, kwargs)

    def describe(self, request, kwargs):
        super().describe(request, kwargs)

    def example_manifest(self, request, kwargs):
        super().example_manifest(request, kwargs)

    def get(self, request, kwargs):
        super().get(request, kwargs)

    def logs(self, request, kwargs):
        super().logs(request, kwargs)

    def undeploy(self, request, kwargs):
        super().undeploy(request, kwargs)
