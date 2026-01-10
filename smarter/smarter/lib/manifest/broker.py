# pylint: disable=W0613,C0302
"""Smarter API Manifest Abstract Broker class."""

import logging
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from functools import cached_property
from http import HTTPStatus
from typing import Any, Optional, Type, Union
from urllib.parse import parse_qs, urlparse

import inflect
from django.db import models
from django.http import HttpRequest, QueryDict
from requests import PreparedRequest
from rest_framework.serializers import ModelSerializer

from smarter.apps.account.models import Account, Secret, User, UserProfile
from smarter.common.api import SmarterApiVersions
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import (
    formatted_text,
    formatted_text_green,
    formatted_text_red,
)
from smarter.lib import json
from smarter.lib.cache import cache_results
from smarter.lib.django import waffle
from smarter.lib.django.mixins import SmarterConverterMixin
from smarter.lib.django.model_helpers import TimestampedModel
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.django.waffle import SmarterWaffleSwitches
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
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.models import AbstractSAMBase

from .exceptions import SAMExceptionBase


inflect_engine = inflect.engine()

SUPPORTED_API_VERSIONS = [SmarterApiVersions.V1]


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.MANIFEST_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


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


class AbstractBroker(ABC, SmarterRequestMixin, SmarterConverterMixin):
    """
    Abstract base class for the Smarter Broker Model.

    This class defines the core broker service pattern for the Smarter API, and is the
    foundation for all concrete Broker implementations. Brokers are responsible for
    processing Smarter YAML manifests, initializing Pydantic models, and brokering
    the correct implementation class for CLI and API operations.

    Responsibilities
    ----------------
    - Load, partially validate, and parse a Smarter API YAML manifest, sufficient to
      initialize a Pydantic model.
    - Implement the broker service pattern for the underlying object.
    - Initialize the corresponding Pydantic models.
    - Instantiate the underlying Python object for the resource.

    The broker pattern provides generic services for manifest operations, including:
    ``get``, ``post``, ``put``, ``delete``, and ``patch``.

    Subclasses must implement the abstract methods to provide resource-specific
    logic for CLI and API commands such as ``apply``, ``describe``, ``delete``,
    ``deploy``, ``example_manifest``, ``get``, ``logs``, and ``undeploy``.
    """

    _api_version: str = SmarterApiVersions.V1
    _loader: Optional[SAMLoader] = None
    _manifest: Optional[Union[AbstractSAMBase, dict]] = None
    _pydantic_model: Type[AbstractSAMBase] = AbstractSAMBase
    _name: Optional[str] = None
    _kind: Optional[str] = None
    _validated: bool = False
    _thing: Optional[SmarterJournalThings] = None
    _created: bool = False

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        request: HttpRequest,
        *args,
        name: Optional[str] = None,
        kind: Optional[str] = None,
        loader: Optional[SAMLoader] = None,
        api_version: str = SmarterApiVersions.V1,
        manifest: Optional[Union[dict, AbstractSAMBase]] = None,
        file_path: Optional[str] = None,
        url: Optional[str] = None,
        **kwargs,
    ):
        logger.debug(
            (
                "%s.__init__() called with request=%s, name=%s, kind=%s, "
                "loader=%s, api_version=%s, manifest=%s, file_path=%s, url=%s, "
                "args=%s, kwargs=%s"
            ),
            self.abstract_broker_logger_prefix,
            request,
            name,
            kind,
            loader,
            api_version,
            manifest,
            file_path,
            url,
            args,
            kwargs,
        )
        # ----------------------------------------------------------------------
        # Initial resolution of parameters, taking into consideration that
        # they may be passed in via args or kwargs.
        # ----------------------------------------------------------------------
        user = kwargs.pop("user", None) or next((arg for arg in args if isinstance(arg, User)), None)
        account = kwargs.pop("account", None) or next((arg for arg in args if isinstance(arg, Account)), None)
        user_profile = kwargs.pop("user_profile", None) or next(
            (arg for arg in args if isinstance(arg, UserProfile)), None
        )
        SmarterRequestMixin.__init__(
            self, request, *args, user=user, account=account, user_profile=user_profile, **kwargs
        )

        # ----------------------------------------------------------------------
        # Set API version, name, and kind.
        # These will presumably be overridden once a manifest or loader
        # is provided.
        # ----------------------------------------------------------------------
        self.api_version = api_version or SmarterApiVersions.V1
        name = name or kwargs.pop("name", None)
        self.name_cached_property_setter(name)
        self.kind_setter(kind or kwargs.pop("kind", None))

        # ----------------------------------------------------------------------
        # Manifest and SAMLoader resolution logic. Prioritize the manifest
        # if provided, otherwise attempt to initialize the SAMLoader from
        # the params, which in turn will lazily load the manifest if/when needed.
        # ----------------------------------------------------------------------
        manifest = (
            manifest
            or kwargs.pop("manifest", manifest)
            or next((arg for arg in args if isinstance(arg, AbstractSAMBase)), None)
        )
        if manifest:
            self.manifest_setter(manifest)
        else:
            loader = (
                loader or kwargs.pop("loader", None) or next((arg for arg in args if isinstance(arg, SAMLoader)), None)
            )
            if loader:
                self.loader = loader
            else:
                if isinstance(file_path, str):
                    if self._loader:
                        logger.warning(
                            f"{self.abstract_broker_logger_prefix}.__init__() - Both loader and file_path provided. "
                            f"file_path will override loader."
                        )
                    self.loader = SAMLoader(file_path=file_path)
                    if self._loader.ready:
                        self.kind_setter(self._loader.manifest_kind)
                        name = self._loader.manifest_metadata.get("name")
                        self.name_cached_property_setter(name)  # type: ignore

        self._validated = bool(self._manifest) or bool(self._loader and self.loader.ready)

        # ----------------------------------------------------------------------
        # log initialization state.
        # ----------------------------------------------------------------------
        self.log_abstract_broker_state()

    def __str__(self):
        """
        Returns the string representation of the broker, expresssed as
        "{apiVersion} {kind} Broker".

        example: "smarter.sh/v1 ChatBot Broker"

        :return: The string representation of the broker.
        :rtype: str
        """
        account = self.account.name or "Anonymous"
        name = self.name or "Unknown"

        return f"{formatted_text(self.__class__.__name__)}(version={self.api_version}, account={account}, name={name})"

    def __repr__(self) -> str:
        """
        Returns the JSON representation of the broker.

        :return: The JSON representation of the broker.
        :rtype: str
        """
        return json.dumps(self.to_json(), indent=4)

    def __bool__(self) -> bool:
        """
        Return True if the broker is ready for operations.

        :return: True if the broker is ready for operations.
        :rtype: bool
        """
        return self.ready

    def __hash__(self) -> int:
        """
        Return the hash of the broker based on account, kind, and name.

        :return: The hash of the broker.
        :rtype: int
        """
        return hash((self.account, self.kind, self.name))

    def __eq__(self, other: object) -> bool:
        """
        Check if two brokers are equal based on account, kind, and name.

        :param other: The other broker to compare.
        :type other: object
        :return: True if the brokers are equal, False otherwise.
        :rtype: bool
        """
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.account == other.account and self.kind == other.kind and self.name == other.name

    def __lt__(self, other: object) -> bool:
        """
        Less than comparison based on account, kind, and name.

        :param other: The other broker to compare.
        :type other: object
        :return: True if this broker is less than the other broker, False otherwise.
        :rtype: bool
        """
        if not isinstance(other, self.__class__):
            return NotImplemented
        return (self.account, self.kind, self.name) < (other.account, other.kind, other.name)

    def __le__(self, other: object) -> bool:
        """
        Less than or equal comparison based on account, kind, and name.

        :param other: The other broker to compare.
        :type other: object
        :return: True if this broker is less than or equal to the other broker, False otherwise.
        :rtype: bool
        """
        if not isinstance(other, self.__class__):
            return NotImplemented
        return (self.account, self.kind, self.name) <= (other.account, other.kind, other.name)

    def __gt__(self, other: object) -> bool:
        """
        Greater than comparison based on account, kind, and name.

        :param other: The other broker to compare.
        :type other: object
        :return: True if this broker is greater than the other broker, False otherwise.
        :rtype: bool
        """
        if not isinstance(other, self.__class__):
            return NotImplemented
        return (self.account, self.kind, self.name) > (other.account, other.kind, other.name)

    def __ge__(self, other: object) -> bool:
        """
        Greater than or equal comparison based on account, kind, and name.

        :param other: The other broker to compare.
        :type other: object
        :return: True if this broker is greater than or equal to the other broker, False otherwise.
        :rtype: bool
        """
        if not isinstance(other, self.__class__):
            return NotImplemented
        return (self.account, self.kind, self.name) >= (other.account, other.kind, other.name)

    ###########################################################################
    # Class Instance Properties
    ###########################################################################
    @property
    def abstract_broker_logger_prefix(self) -> str:
        """Return the logger prefix for the AbstractBroker.

        :return: The logger prefix for the AbstractBroker.
        :rtype: str
        """
        return formatted_text(f"{__name__}.{AbstractBroker.__name__}[{id(self)}]")

    @property
    def is_ready_abstract_broker(self) -> bool:
        """Return True if the AbstractBroker is ready for operations.

        An AbstractBroker is considered ready if:
        - The AccountMixin is ready.
        - The RequestMixin is ready.
        - either a valid manifest is loaded or a ready SAMLoader is present.

        :return: True if the AbstractBroker is ready for operations.
        :rtype: bool
        """
        if not self.is_accountmixin_ready:
            logger.warning(
                "%s.is_ready_abstract_broker() - AccountMixin is not ready. Cannot process broker.",
                self.abstract_broker_logger_prefix,
            )
            return False
        if not self.is_requestmixin_ready:
            logger.warning(
                "%s.is_ready_abstract_broker() - RequestMixin is not ready. Cannot process broker.",
                self.abstract_broker_logger_prefix,
            )
            return False
        if bool(self._manifest):
            logger.debug(
                "%s.is_ready_abstract_broker() returning true because manifest is loaded.",
                self.abstract_broker_logger_prefix,
            )
            return True
        if bool(self.loader) and self.loader.ready:
            logger.debug(
                "%s.is_ready_abstract_broker() returning true because loader is ready.",
                self.abstract_broker_logger_prefix,
            )
            return True
        if not bool(self._manifest):
            logger.warning(
                "%s.is_ready_abstract_broker() returning false because manifest is not loaded.",
                self.abstract_broker_logger_prefix,
            )
        if not bool(self.loader) or not self.loader.ready:
            logger.warning(
                "%s.is_ready_abstract_broker() returning false because loader is not ready.",
                self.abstract_broker_logger_prefix,
            )
        return False

    @property
    def abstract_broker_ready_state(self) -> str:
        """Return a string representation of the AbstractBroker's ready state.

        :return: "READY" if the AbstractBroker is ready, otherwise "NOT_READY".
        :rtype: str
        """
        if self.is_ready_abstract_broker:
            return formatted_text_green("READY")
        return formatted_text_red("NOT_READY")

    @property
    def ready(self) -> bool:
        """Return True if the broker is ready for operations.

        A broker is considered ready if it has a valid manifest loaded.

        :return: True if the broker is ready for operations.
        :rtype: bool
        """
        retval = super().ready
        if not retval:
            logger.warning(
                "%s.ready() SmarterRequestMixin is not ready for kind=%s",
                self.abstract_broker_logger_prefix,
                self.kind,
            )
            return False
        return retval and self.is_ready_abstract_broker

    @property
    def ready_state(self) -> str:
        """Return a string representation of the broker's ready state.

        :return: "READY" if the broker is ready, otherwise "NOT_READY".
        :rtype: str
        """
        if self.ready:
            return formatted_text_green("READY")
        return formatted_text_red("NOT_READY")

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the formatted class name for logging purposes.
        This is used to provide a more readable class name in logs.

        :return: The formatted class name.
        :rtype: str
        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.{AbstractBroker.__name__}()"

    @property
    def request(self) -> Optional[HttpRequest]:
        """Return the request object.

        :return: The request object.
        :rtype: Optional[HttpRequest]
        """
        return self.smarter_request

    @property
    def params(self) -> Optional[QueryDict]:
        """
        Return the query parameters from the url of the request. there are two
        scenarios to consider:
        1. the request is a Django HttpRequest object (the expected case)
        2. the request is a Python PreparedRequest object (the edge case)

        :return: The query parameters from the url of the request.
        :rtype: Optional[QueryDict]
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
        """Return the full uri of the request.

        :return: The full uri of the request.
        :rtype: Optional[str]
        """
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
        """Return True if the broker was created successfully.

        :return: True if the broker was created successfully.
        :rtype: bool
        """
        return self._created

    @property
    def is_valid(self) -> bool:
        return self._validated

    @property
    def thing(self) -> SmarterJournalThings:
        """
        The Smarter Journal Thing for this broker.

        :return: The Smarter Journal Thing for this broker.
        :rtype: SmarterJournalThings, an enumeration of all Smarter AI resource types.
        """
        if not self._thing:
            self._thing = SmarterJournalThings(self.kind)
        return self._thing

    @property
    def kind(self) -> Optional[str]:
        """
        The kind of manifest.

        :return: The kind of manifest.
        :rtype: Optional[str]
        """
        return self._kind

    def kind_setter(self, value: str):
        """
        Set the kind of manifest. Validates that the kind is a
        valid SmarterJournalThings value.

        :raises SmarterValueError: If the kind is not valid.

        :param value: The kind of manifest to set.
        :type value: str
        """
        if value is None:
            logger.warning(
                "%s.kind() setter - cannot unset kind. Ignoring this operation.",
                self.abstract_broker_logger_prefix,
            )
            return
        if not isinstance(value, str):
            raise SmarterValueError(f"kind must be a string. Got: {type(value)} {value}")
        if not value in SmarterJournalThings.all_values():
            raise SmarterValueError(
                f"kind '{value}' is not a valid SmarterJournalThings value. Expected one of: {SmarterJournalThings.all_values()}"
            )

        self._kind = value
        logger.debug("%s.kind() setter set kind to %s", self.abstract_broker_logger_prefix, self._kind)

    @cached_property
    def name(self) -> Optional[str]:
        """
        Retrieve the unique name identifier for the ChatBot instance managed by this broker.

        This property accesses the name used to distinguish the ChatBot within the database and across
        the Smarter platform. The name is first returned from an internal cache if available. If not cached,
        and if a manifest is present, the name is extracted from the manifest's metadata and stored for
        subsequent access.

        The name is essential for database queries, model lookups, and for associating related resources
        such as API keys, plugins, and functions with the correct ChatBot instance.

        :returns: The name of the ChatBot as a string, or ``None`` if the name is not set or cannot be determined.
        :rtype: Optional[str]

        .. note::

            The name property is a critical identifier used throughout the broker to ensure correct
            mapping between manifest data and persistent application state.
        """
        if self._name:
            return self._name
        if self._manifest:
            self._name = self.manifest.metadata.name
            logger.debug(
                "%s.name() set name to %s from manifest metadata", self.abstract_broker_logger_prefix, self._name
            )
            return self._name
        else:
            logger.debug("%s.name() manifest is not set.", self.abstract_broker_logger_prefix)
        if self.loader:
            logger.debug(
                "%s.name() found a SAMLoader. Attempting to initialize the manifest.",
                self.abstract_broker_logger_prefix,
            )
            if self.manifest:
                self._name = self.manifest.metadata.name
                logger.debug(
                    "%s.name() set name to %s from manifest metadata", self.abstract_broker_logger_prefix, self._name
                )
                return self._name
            else:
                self._name = self.loader.manifest_metadata.get("name")
                if self._name:
                    logger.debug(
                        "%s.name() set name to %s from loader metadata", self.abstract_broker_logger_prefix, self._name
                    )
                    return self._name
                logger.debug("%s.name() loader metadata does not contain a name", self.abstract_broker_logger_prefix)
        if isinstance(self.params, QueryDict):
            name_param = self.params.get("name", None)
            if name_param:
                self._name = name_param
                logger.debug(
                    "%s.name() set name to %s from name url param", self.abstract_broker_logger_prefix, self._name
                )
            else:
                logger.debug("%s.name() url params do not contain a name", self.abstract_broker_logger_prefix)
        if not self._name:
            logger.warning("%s.name() could not determine name, returning None", self.abstract_broker_logger_prefix)
        return self._name

    def name_cached_property_setter(self, value: str):
        """
        A workaround to the limitation that you cannot use both @cached_property and
        a setter for the same attribute name (name). In Python, you cannot have a
        property (or cached_property) and a setter with the same name unless you use the
        @property decorator (not @cached_property).

        We need the cached_property so that the lazy evaluation of the name only happens
        once, and subsequent accesses return the cached value for performance.
        However, we also need to be able to set the name explicitly in some cases,

        :param value: The name to set for the manifest.
        :type value: str
        """
        if not type(value) in [str, type(None)]:
            raise SmarterValueError("name must be a string or None")

        self._name = value
        # Delete cached_property value if present
        try:
            del self.__dict__["name"]
            logger.debug("%s.name() setter cleared cached_property", self.abstract_broker_logger_prefix)
        except KeyError:
            pass
        logger.debug("%s.name() setter set name to %s", self.abstract_broker_logger_prefix, self._name)

    @property
    def api_version(self) -> str:
        """
        The API version of the manifest.

        :return: The API version of the manifest.
        :rtype: Optional[str]
        """
        return self._api_version

    @api_version.setter
    def api_version(self, value: str):
        """
        Set the API version of the manifest.

        :param value: The API version to set.
        :type value: str
        """
        if not isinstance(value, str):
            raise SmarterValueError("api_version must be a string")
        self._api_version = value
        logger.debug(
            "%s.api_version() setter set api_version to %s", self.abstract_broker_logger_prefix, self._api_version
        )

    @property
    def loader(self) -> Optional[SAMLoader]:
        """
        The SAMLoader instance for this broker.

        :return: The SAMLoader instance for this broker.
        :rtype: Optional[SAMLoader]
        """
        if self._loader and self._loader.ready:
            return self._loader

    @loader.setter
    def loader(self, value: SAMLoader):
        """
        Set the SAMLoader instance for this broker.

        :param value: The SAMLoader instance to set.
        :type value: SAMLoader
        """
        if not value:
            self._loader = None
            logger.debug(
                "%s.loader() setter - unset loader.",
                self.abstract_broker_logger_prefix,
            )
            return
        if not isinstance(value, SAMLoader):
            raise SmarterValueError("loader must be a SAMLoader instance")
        self._loader = value
        if self._loader.ready:
            # initialize the manifest from the loader
            assert self.manifest is not None

        logger.debug("%s.loader() setter set loader to %s", self.abstract_broker_logger_prefix, self._loader)

    ###########################################################################
    # Abstract Properties
    ###########################################################################
    @property
    @abstractmethod
    def SerializerClass(self) -> Type[ModelSerializer]:
        """
        Return the serializer class for the broker.

        :return: The serializer class definition for the broker.
        :rtype: Type[ModelSerializer]
        """
        raise SAMBrokerErrorNotImplemented(message="", thing=self.thing, command=None)

    @property
    @abstractmethod
    def ORMModelClass(self) -> Type[TimestampedModel]:
        """
        Return the Django ORM model class for the broker.

        :return: The Django ORM model class definition for the broker.
        :rtype: Type[TimestampedModel]
        """
        raise SAMBrokerErrorNotImplemented(
            message="Subclasses must implement the ModelClass", thing=self.thing, command=None
        )

    @property
    def SAMModelClass(self) -> Type[AbstractSAMBase]:
        """
        Return the SAM (Smarter Api Manifest) model class for the broker.

        :return: The Pydantic model class definition for the broker.
        :rtype: Type[AbstractSAMBase]
        """
        return self._pydantic_model

    @property
    @abstractmethod
    def manifest(self) -> Optional[Union[AbstractSAMBase, dict]]:
        """
        The Pydantic model representing the manifest. If the manifest
        has not been initialized yet, this property will attempt to
        initialize it using the SAMLoader.

        :return: The Pydantic model representing the manifest.
        :rtype: Optional[AbstractSAMBase]
        """
        raise SAMBrokerErrorNotImplemented("Subclasses must implement the manifest property.")

    def manifest_setter(self, value: Optional[Union[AbstractSAMBase, dict[str, Any]]]):
        """
        Set the manifest for the broker and override all AbstractBroker
        model properties based on the manifest data.

        :param value: The manifest to set, either as a Pydantic model or a dictionary.
        :type value: Optional[Union[AbstractSAMBase, dict]]
        """
        if value is None:
            self._manifest = None
            logger.debug(
                "%s.manifest() setter - unset manifest.",
                self.abstract_broker_logger_prefix,
            )
            return
        if isinstance(value, AbstractSAMBase):
            self._manifest = value
            self._api_version = self._manifest.apiVersion
            self.name_cached_property_setter(self._manifest.metadata.name)
            self.kind_setter(self._manifest.kind)
            self.loader = SAMLoader(manifest=self._manifest.model_dump())
            logger.debug(
                "%s.manifest() setter set manifest from Pydantic model: %s",
                self.abstract_broker_logger_prefix,
                self._manifest,
            )
        elif isinstance(value, dict):
            self._manifest = value
            self.api_version = self._manifest.get("apiVersion")
            name = self._manifest.get("metadata", {}).get("name")
            self.name_cached_property_setter(name)
            kind = self._manifest.get("kind")
            if not isinstance(kind, str):
                raise SmarterValueError("manifest kind must be a string")
            self.kind_setter(kind)
            self.loader = SAMLoader(manifest=self._manifest)

            logger.debug(
                "%s.manifest() setter set manifest from dict: %s",
                self.abstract_broker_logger_prefix,
                self._manifest,
            )
        if self._manifest:
            self._validated = True
            self._created = True
        else:
            raise SmarterValueError("manifest must be a SAM model (ie Pydantic model) or a dict")

    ###########################################################################
    # Abstract Methods
    ###########################################################################
    # mcdaniel: there's a reason why this is not an abstract method, but i forget why.
    def apply(self, request: HttpRequest, *args, **kwargs) -> Optional[SmarterJournaledJsonResponse]:
        """
        Apply a manifest, which works like an upsert operation. Designed
        around the Kubernetes ``kubectl apply`` command.

        This method processes a Smarter YAML manifest and either creates or updates
        the corresponding resource, depending on whether it already exists.

        Example manifest metadata::

            metadata:
                description: new description
                name: test71d12b8212b628df
                version: 1.0.0

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A SmarterJournaledJsonResponse if implemented, otherwise None.
        :rtype: Optional[SmarterJournaledJsonResponse]

        .. todo:: Research why this is not an abstract method.
        """
        logger.debug(
            "%s.apply() called %s with args: %s, kwargs: %s, account: %s, user: %s",
            self.abstract_broker_logger_prefix,
            request,
            args,
            kwargs,
            self.account,
            self.user,
        )

    @abstractmethod
    def chat(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Invoke a chat operation.

        This abstract method should be implemented by subclasses to provide
        chat-based interactions with the broker resource.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A SmarterJournaledJsonResponse containing the chat response.
        :rtype: SmarterJournaledJsonResponse
        """
        raise SAMBrokerErrorNotImplemented(
            message="chat() not implemented", thing=self.thing, command=SmarterJournalCliCommands.CHAT
        )

    @abstractmethod
    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """describe a resource.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A SmarterJournaledJsonResponse containing the description of the resource.
        :rtype: SmarterJournaledJsonResponse
        """
        raise SAMBrokerErrorNotImplemented(
            message="describe() not implemented", thing=self.thing, command=SmarterJournalCliCommands.DESCRIBE
        )

    @abstractmethod
    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """delete a resource.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A SmarterJournaledJsonResponse containing the result of the delete operation.
        :rtype: SmarterJournaledJsonResponse
        """
        raise SAMBrokerErrorNotImplemented(
            message="delete() not implemented", thing=self.thing, command=SmarterJournalCliCommands.DELETE
        )

    @abstractmethod
    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """deploy a resource.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A SmarterJournaledJsonResponse containing the result of the deploy operation.
        :rtype: SmarterJournaledJsonResponse
        """
        raise SAMBrokerErrorNotImplemented(
            message="deploy() not implemented", thing=self.thing, command=SmarterJournalCliCommands.DEPLOY
        )

    @abstractmethod
    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Returns an example yaml manifest document for the kind of resource.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A SmarterJournaledJsonResponse containing the example manifest.
        :rtype: SmarterJournaledJsonResponse
        """
        raise SAMBrokerErrorNotImplemented(
            message="example_manifest() not implemented",
            thing=self.thing,
            command=SmarterJournalCliCommands.MANIFEST_EXAMPLE,
        )

    @abstractmethod
    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """get information about specified resources.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A SmarterJournaledJsonResponse containing the result of the get operation.
        :rtype: SmarterJournaledJsonResponse
        """
        raise SAMBrokerErrorNotImplemented(
            message="get() not implemented", thing=self.thing, command=SmarterJournalCliCommands.GET
        )

    @abstractmethod
    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """get logs for a resource.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A SmarterJournaledJsonResponse containing the logs for the resource.
        :rtype: SmarterJournaledJsonResponse
        """
        raise SAMBrokerErrorNotImplemented(
            message="logs() not implemented", thing=self.thing, command=SmarterJournalCliCommands.LOGS
        )

    @abstractmethod
    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """undeploy a resource.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A SmarterJournaledJsonResponse containing the result of the undeploy operation.
        :rtype: SmarterJournaledJsonResponse
        """
        raise SAMBrokerErrorNotImplemented(
            message="undeploy() not implemented", thing=self.thing, command=SmarterJournalCliCommands.UNDEPLOY
        )

    def schema(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return the published JSON schema for the Pydantic model.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A SmarterJournaledJsonResponse containing the JSON schema.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)

        model = self.SAMModelClass
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

        :param user_profile: The UserProfile to associate the secret with.
        :type user_profile: UserProfile
        :param name: The name of the secret.
        :type name: str
        :param value: The value of the secret.
        :type value: Optional[str]
        :param description: A description of the secret.
        :type description: Optional[str]
        :param expiration: The expiration date of the secret.
        :type expiration: Optional[datetime]
        :return: The created or retrieved Secret object.
        :rtype: Secret
        """

        @cache_results()
        def cached_secret_by_name_and_profile_id(name: str, profile_id: int) -> Optional[Secret]:
            try:
                return Secret.objects.get(name=name, user_profile__id=profile_id)
            except Secret.DoesNotExist:
                return None

        secret: Optional[Secret] = None
        try:
            secret = cached_secret_by_name_and_profile_id(name=name, profile_id=user_profile.id)
        except Secret.DoesNotExist as e:
            logger.debug(
                "%s.get_or_create_secret() Secret %s not found for user %s",
                self.abstract_broker_logger_prefix,
                name,
                user_profile.user.username,
            )
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

        if not secret:
            raise SAMBrokerError(
                message=f"Failed to create or retrieve Secret {name}",
                thing=self.thing,
                command=SmarterJournalCliCommands.GET,
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
        """Return a common success response.

        :param command: The command that was executed.
        :type command: SmarterJournalCliCommands
        :param data: The data to return in the response.
        :type data: Optional[dict]
        :param message: An optional message to include in the response.
        :type message: Optional[str]
        :return: A SmarterJournaledJsonResponse containing the success response.
        :rtype: SmarterJournaledJsonResponse
        """
        if self.request is None:
            raise SAMBrokerError(
                message="Cannot create JSON response without a valid request object",
                thing=self.thing,
                command=command,
            )
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
        """Return a common read-only response.

        :param command: The command that was executed.
        :type command: SmarterJournalCliCommands
        :return: A SmarterJournaledJsonResponse containing the read-only response.
        :rtype: SmarterJournaledJsonResponse
        """
        if self.request is None:
            raise SAMBrokerError(
                message="Cannot create JSON response without a valid request object",
                thing=self.thing,
                command=command,
            )
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
        """Return a common not implemented response.

        :param command: The command that was executed.
        :type command: SmarterJournalCliCommands
        :return: A SmarterJournaledJsonResponse containing the not implemented response.
        :rtype: SmarterJournaledJsonResponse
        """
        if self.request is None:
            raise SAMBrokerError(
                message="Cannot create JSON response without a valid request object",
                thing=self.thing,
                command=command,
            )
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
        """Return a common not ready response.

        :param command: The command that was executed.
        :type command: SmarterJournalCliCommands
        :return: A SmarterJournaledJsonResponse containing the not ready response.
        :rtype: SmarterJournaledJsonResponse
        """
        if self.request is None:
            raise SAMBrokerError(
                message="Cannot create JSON response without a valid request object",
                thing=self.thing,
                command=command,
            )
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
        """Return a common not found response.

        :param command: The command that was executed.
        :type command: SmarterJournalCliCommands
        :param message: An optional custom message to include in the response.
        :type message: Optional[str]
        :return: A SmarterJournaledJsonResponse containing the not found response.
        :rtype: SmarterJournaledJsonResponse
        """
        if self.request is None:
            raise SAMBrokerError(
                message="Cannot create JSON response without a valid request object",
                thing=self.thing,
                command=command,
            )
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

        :param command: The command that was executed.
        :type command: SmarterJournalCliCommands
        :param e: The exception that was raised.
        :type e: Exception
        :return: A SmarterJournaledJsonResponse containing the error response.
        :rtype: SmarterJournaledJsonResponse
        """
        if self.request is None:
            raise SAMBrokerError(
                message="Cannot create JSON response without a valid request object",
                thing=self.thing,
                command=command,
            )
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

        :param command: The command being executed, for error reporting purposes.
        :type command: Optional[SmarterJournalCliCommands]
        :raises SAMBrokerErrorNotReady: If neither a manifest nor a name param is provided.
        :return: None
        """
        name = kwargs.get("name")
        if name:
            self.name_cached_property_setter(name)

    # pylint: disable=W0212
    def get_model_titles(self, serializer: ModelSerializer) -> Optional[list[dict[str, str]]]:
        """
        For tabular output from get() implementations. Returns a list of field names and types
        from the Django model serializer.

        :param serializer: The Django model serializer instance.
        :type serializer: ModelSerializer
        :return: A list of field names and types.
        :rtype: Optional[list[dict[str, str]]]
        """
        fields_and_types: list[dict[str, str]] = []
        for field_name, field in serializer.fields.items():
            item = self.snake_to_camel({"name": field_name, "type": type(field).__name__}, convert_values=True)
            if isinstance(item, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in item.items()):
                fields_and_types.append(item)
            else:
                logger.warning(
                    "%s.get_model_titles() skipping field %s: expected dict with str keys and str values but got: %s",
                    self.abstract_broker_logger_prefix,
                    field_name,
                    item,
                )
        return fields_and_types

    def clean_cli_param(self, param, param_name: str = "unknown", url: Optional[str] = None) -> Optional[str]:
        """
        - Remove any leading or trailing whitespace from the param.
        - Ensure that the param is a string.
        - Return the cleaned param.

        :param param: The param to clean.
        :type param: Any
        :param param_name: The name of the param, for logging purposes.
        :type param_name: str
        :param url: The url from which the param was extracted, for logging purposes.
        :type url: Optional[str]
        :return: The cleaned param.
        :rtype: Optional[str]
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

    def to_json(self) -> dict[str, Any]:
        """
        Serialize the broker instance to a JSON string.

        :return: A JSON string representation of the broker instance.
        :rtype: str
        """
        return self.sorted_dict(
            {
                "api_version": self.api_version,
                "kind": self.kind,
                "name": self.name,
                "manifest": self.manifest.model_dump() if isinstance(self.manifest, AbstractSAMBase) else self.manifest,
                "loader": self.loader.to_json() if self.loader else None,
                **super().to_json(),
            }
        )

    def log_abstract_broker_state(self):
        """
        Log the current state of the AbstractBroker instance for debugging purposes.

        :return: None
        """
        msg = (
            f"{self.abstract_broker_logger_prefix}.__init__() - finished initializing {self.kind} "
            f"broker is {self.abstract_broker_ready_state} with "
            f"name: {self._name}, "
            f"manifest: {bool(self._manifest)}, "
            f"loader: {bool(self._loader)}, "
            f"request: {self.url}, "
            f"user_profile: {self.user_profile} "
        )
        if self.is_ready_abstract_broker:
            logger.info(msg)
        else:
            logger.warning(msg)


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

    @property
    def ORMModelClass(self) -> Type[models.Model]:
        raise SAMBrokerErrorNotImplemented(
            message="Subclasses must implement the ORMModelClass", thing=self.thing, command=None
        )

    @property
    def SerializerClass(self) -> Type[ModelSerializer]:
        raise SAMBrokerErrorNotImplemented(
            message="Subclasses must implement the SerializerClass", thing=self.thing, command=None
        )

    @property
    def manifest(self) -> Optional[Union[AbstractSAMBase, dict]]:
        raise SAMBrokerErrorNotImplemented("Subclasses must implement the manifest property.")

    def chat(self, request, *args, **kwargs):
        super().chat(request, args, kwargs)

    def delete(self, request, *args, **kwargs):
        super().delete(request, args, kwargs)

    def deploy(self, request, *args, **kwargs):
        super().deploy(request, args, kwargs)

    def describe(self, request, *args, **kwargs):
        super().describe(request, args, kwargs)

    def example_manifest(self, request, *args, **kwargs):
        super().example_manifest(request, args, kwargs)

    def get(self, request, *args, **kwargs):
        super().get(request, args, kwargs)

    def logs(self, request, *args, **kwargs):
        super().logs(request, args, kwargs)

    def undeploy(self, request, *args, **kwargs):
        super().undeploy(request, args, kwargs)
