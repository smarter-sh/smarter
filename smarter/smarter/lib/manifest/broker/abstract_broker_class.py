# pylint: disable=C0302
"""Smarter API Manifest Abstract Broker class."""

import contextlib
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from functools import cached_property, wraps
from http import HTTPStatus
from typing import (
    Any,
    Callable,
    ClassVar,
    Generic,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)
from urllib.parse import parse_qs, urlparse

import inflect
from django.core import serializers
from django.core.handlers.asgi import ASGIRequest
from django.db import IntegrityError, models
from django.dispatch import Signal
from django.http import HttpRequest, QueryDict
from pydantic import ValidationError
from requests import PreparedRequest
from rest_framework.request import Request
from rest_framework.serializers import ModelSerializer

from smarter.apps.account.models import (
    Account,
    MetaDataWithOwnershipModel,
    User,
    UserProfile,
)
from smarter.apps.account.signals import cache_invalidate
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
    smarter_cached_objects,
)
from smarter.apps.secret.models import Secret
from smarter.common.api import SmarterApiVersions
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json, logging
from smarter.lib.annotation.const import ANNOTATION_SELECTOR_PARAM
from smarter.lib.annotation.selectors import QuerySetType, filter_by_annotations
from smarter.lib.django import waffle
from smarter.lib.django.models import MetaDataModel
from smarter.lib.django.models.utils import assign_changed_fields, tags_changed
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
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.keys import unknown_keys
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.models import (
    AbstractSAMBase,
    SAMDependencyTreeNode,
    client_manifest_validation,
)
from smarter.lib.manifest.record_locator import console_url
from smarter.lib.typing import SmarterDictType

from .error_classes import (
    SAMBrokerError,
    SAMBrokerErrorDependencies,
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
    SAMBrokerInternalError,
    SAMBrokerReadOnlyError,
)
from .result import SAMBrokerCommandResult

inflect_engine = inflect.engine()

SUPPORTED_API_VERSIONS = [SmarterApiVersions.V1]
SmarterRequest = Union[HttpRequest, Request, ASGIRequest]
OwnedModelT = TypeVar("OwnedModelT", bound=MetaDataModel)
"""A Django ORM model that has a name and an owner, as :meth:`AbstractBroker.get_owned_object` looks up.

E.g. a ``MetaDataWithOwnershipModel``, or a ``Budget``.
"""
ModelT = TypeVar("ModelT", bound=models.Model)
"""The Django ORM model of a broker's resource, its :attr:`AbstractBroker.ORMModelClass`."""
MetaModelT = TypeVar("MetaModelT", bound=models.Model)
"""The Django ORM model that holds a broker's resource's name and owner, its :attr:`AbstractBroker.ORMMetaModelClass`.

For most kinds it is the same model as :data:`ModelT`. A plugin's is its ``PluginMeta``.
"""

KNOWN_KINDS: frozenset[str] = frozenset(SmarterJournalThings.all())
"""Every valid broker kind.

An enum's members are fixed, so the set is built once.
"""


# pylint: disable=W0613
def should_log(level: int) -> bool:
    """
    Return True if the ``MANIFEST_LOGGING`` waffle switch is on, for the module's waffle-switched logger.

    :param level: The log level. Not used: the switch turns every level on or off.
    :returns: Whether the switch is on.
    """
    return waffle.switch_is_active(SmarterWaffleSwitches.MANIFEST_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


def memoized_dependencies(func: Callable[..., List["SAMDependency"]]) -> Callable[..., List["SAMDependency"]]:
    """Memoize a broker's :meth:`AbstractBroker.dependencies` for the life of the broker instance.

    The dependencies are queried, and their brokers built, once per broker instance.
    :meth:`AbstractBroker.verify_no_dependencies` clears the memo before it checks, so that
    a delete always sees the current dependencies.

    Example:

    .. code-block:: python

        class SAMGuardrailBroker(AbstractBroker):

            @memoized_dependencies
            def dependencies(self) -> List[AbstractBroker]:
                ...

    :param func: The broker's ``dependencies()`` method.
    :return: The memoized method.
    """

    # pylint: disable=W0212
    @wraps(func)
    def wrapper(self: "AbstractBroker") -> List["SAMDependency"]:
        if self._dependencies is None:
            self._dependencies = func(self)
        return self._dependencies

    return wrapper


class SAMDependencyReference:
    """The kind, name and owner of a dependent resource whose broker could not be initialized.

    :meth:`AbstractBroker.dependency_broker` returns one when a dependent resource's broker
    raises during initialization, for example a plugin whose stored model was later removed
    from the list of valid models. It keeps the dependency visible, so that
    :meth:`AbstractBroker.verify_no_dependencies` still refuses to delete the resource it
    depends on, and ``describe`` still lists it in ``status.dependencies``.

    Example:

    .. code-block:: python

        dependency = SAMDependencyReference(kind="Plugin", name="everlasting_gobstopper", user_profile=user_profile)
        print(dependency.kind, dependency.name, dependency.account)

    :param kind: The SAM kind of the resource, e.g. ``SAMKinds.STATIC_PLUGIN.value``.
    :param name: The resource's manifest name.
    :param user_profile: The resource's owner.
    """

    def __init__(self, kind: str, name: str, user_profile: Optional[UserProfile]):
        self.kind = kind
        self.name = name
        self.user_profile = user_profile

    @property
    def account(self) -> Optional[Account]:
        """The account of the resource's owner, if it has one."""
        return self.user_profile.account if self.user_profile else None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(kind={self.kind}, name={self.name}, user_profile={self.user_profile})"


SAMDependency = Union["AbstractBroker", SAMDependencyReference]
"""A resource that depends on another: its broker, or a reference to it when its broker fails to initialize."""

SAMDependents = List[Tuple[Optional[str], Iterable[models.Model]]]
"""
The resources that depend on another, as their Django ORM rows, grouped by SAM kind.

Each pair is a kind, e.g. ``SAMKinds.LLM_CLIENT.value``, and the rows of that kind, usually a
lazy QuerySet. A kind of None means that each row has its own kind, in its ``kind`` field, as a
plugin's PluginMeta does. See :meth:`AbstractBroker.dependents`.
"""


def dependents_exist(rows: Iterable[models.Model]) -> bool:
    """Return True if there is at least one row, reading no more of them than that.

    A QuerySet is asked with one ``EXISTS`` query, and any other iterable is read up to its
    first item, so a generator that filters rows in Python stops at the first match.

    :param rows: The rows of one kind, from :meth:`AbstractBroker.dependents`.
    :return: Whether there is at least one row.
    """
    if isinstance(rows, models.QuerySet):
        return rows.exists()
    return next(iter(rows), None) is not None


RowT = TypeVar("RowT", bound=models.Model)
"""A Django ORM model, as :func:`rows_with_pk` returns rows of."""


def rows_with_pk(manager: "models.Manager[RowT]", pk: Optional[int]) -> "models.QuerySet[RowT]":
    """Return the row with a primary key, as a QuerySet, or an empty QuerySet if the key is None.

    A broker's :meth:`AbstractBroker.references` uses it for a nullable foreign key, e.g.
    ``rows_with_pk(Secret.objects, llmhost.api_key_secret_id)``. Unlike a filter on the reverse
    relation, it also works for an unsaved instance.

    :param manager: The model's manager, e.g. ``Secret.objects``.
    :param pk: The primary key, e.g. a foreign key's id, or None.
    :return: A QuerySet of the row, or an empty QuerySet.
    """
    if pk is None:
        return manager.none()
    rows = manager.filter(pk=pk)
    return rows


def first_arg_of_type(args: Iterable[object], types: Union[type, Tuple[type, ...]]) -> Any:
    """
    Return the first positional argument that is an instance of a type, or None.

    A broker can be passed its request, user, account, user profile, manifest and loader
    positionally, in any order, so :class:`AbstractBroker` finds each by its type.

    :param args: The positional arguments.
    :param types: The type, or a tuple of types, as for :func:`isinstance`.
    :returns: The first argument of that type, or None if there is none.
    """
    for arg in args:
        if isinstance(arg, types):
            return arg
    return None


class AbstractBroker(ABC, SmarterRequestMixin, Generic[ModelT, MetaModelT]):
    """
    Abstract base class for the Smarter Broker Model.

    This class defines the core broker service pattern for the Smarter API, and is the
    foundation for all concrete Broker implementations. Brokers are responsible for
    processing Smarter YAML manifests, initializing Pydantic models, and brokering
    the correct implementation class for CLI and API operations.

    **Responsibilities:**

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

    A broker names its Django ORM models as type arguments, the model of its resource and the
    model that holds the resource's name and owner, e.g. ``AbstractBroker[Secret, Secret]``, or
    ``AbstractBroker[PluginDataBase, PluginMeta]`` for a plugin.
    """

    _api_version: str = SmarterApiVersions.V1
    _loader: Optional[SAMLoader] = None
    _manifest: Optional[Union[AbstractSAMBase, SmarterDictType]] = None
    _pydantic_model: Type[AbstractSAMBase] = AbstractSAMBase
    _name: Optional[str] = None
    _kind: Optional[str] = None
    _validated: bool = False
    _thing: Optional[SmarterJournalThings] = None
    _broker_ready_sent: bool = False

    deployable: ClassVar[bool] = False
    """
    True when the broker implements :meth:`deploy`.

    The cli api's ``resources`` command reports it as each kind's ``Deployable``,
    and the smarter cli offers ``deploy`` and ``undeploy`` commands for those kinds.
    A broker that sets it must override :meth:`deploy`; :meth:`undeploy` may still
    raise :class:`SAMBrokerErrorNotImplemented`, as CustomDomain's and
    LLMHostCompute's do.
    """
    _created: bool = False
    _orm_meta_instance: Optional[MetaModelT] = None
    _orm_instance: Optional[ModelT] = None
    _ready: bool = False
    _is_ready_abstract_broker: bool = False
    _dependencies: Optional[List[SAMDependency]] = None
    _dependency_references_only: bool = False
    """While True, :meth:`dependency_brokers` returns references instead of brokers.

    See :meth:`dependency_references`.
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        request: Optional[HttpRequest],
        *args,
        name: Optional[str] = None,
        kind: Optional[str] = None,
        loader: Optional[SAMLoader] = None,
        api_version: str = SmarterApiVersions.V1,
        manifest: Optional[Union[SmarterDictType, AbstractSAMBase]] = None,
        file_path: Optional[str] = None,
        url: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize the broker from a manifest, a loader, a manifest file, or the Django ORM.

        A manifest takes precedence over a loader, and a loader over a file path. With none of
        them, the broker is initialized from the ORM instance named ``name`` and owned by the
        user profile, if there is one.

        :param request: The request, or None. It may also be passed positionally in ``args``.
        :param args: Positional arguments, among which the request, user, account, user profile,
            manifest and loader are found by their types.
        :param name: The resource's name.
        :param kind: The resource's SAM kind, e.g. ``Guardrail``.
        :param loader: A loader that has read the manifest.
        :param api_version: The manifest's api version.
        :param manifest: The manifest, as a Pydantic model or a dict.
        :param file_path: The path of a manifest file, read when no loader is passed.
        :param url: Accepted, for the same parameters as :class:`~smarter.lib.manifest.loader.SAMLoader`, but not used.
        :param kwargs: ``user``, ``account`` and ``user_profile``, and the rest, which are passed on to
            :class:`~smarter.lib.django.request.SmarterRequestMixin`.
        :raises SmarterValueError: If the kind, name or manifest is invalid.
        :raises SAMBrokerError: If the loader's kind is not the broker's kind.
        """
        # ----------------------------------------------------------------------
        # Attempt to preset the API version, name, and kind.
        #
        # we need this in cases where neither a manifest nor loader is provided.
        # if we have a user_profile and name then we'll be able to attempt
        # to initialize the loader from the ORM, which will in turn allow us to
        # load the manifest.
        # ----------------------------------------------------------------------
        self.api_version = api_version or SmarterApiVersions.V1
        if name:
            self.name_cached_property_setter(name)
        if kind:
            self.kind_setter(kind)

        # ----------------------------------------------------------------------
        # Resolve all initialization parameters to pass to the mixins.
        # ----------------------------------------------------------------------
        # the request can also be a DRF Request or a PreparedRequest, which SmarterRequestMixin accepts
        # although it annotates only HttpRequest. See params.
        if not request:
            request_types = (Request, HttpRequest, ASGIRequest, PreparedRequest)
            found_request = first_arg_of_type(args, request_types)
            request = cast(Optional[HttpRequest], found_request)
        user = kwargs.pop("user", None)
        if not user:
            user = first_arg_of_type(args, User)
        account = kwargs.pop("account", None)
        if not account:
            account = first_arg_of_type(args, Account)
        user_profile = kwargs.pop("user_profile", None)
        if not user_profile:
            user_profile = first_arg_of_type(args, UserProfile)
        SmarterRequestMixin.__init__(
            self, request=request, *args, user=user, account=account, user_profile=user_profile, **kwargs
        )

        # ----------------------------------------------------------------------
        # Manifest and SAMLoader resolution logic. Prioritize the manifest
        # if provided, otherwise attempt to initialize the SAMLoader from
        # the params, which in turn will lazily load the manifest if/when needed.
        # ----------------------------------------------------------------------
        if not manifest:
            manifest = first_arg_of_type(args, AbstractSAMBase)
        if manifest:
            self.manifest_setter(manifest)

        if not loader:
            loader = first_arg_of_type(args, SAMLoader)
        if loader:
            self.loader = loader
        else:
            if isinstance(file_path, str):
                if self._loader:
                    logger.warning(
                        "%s.__init__() - Both loader and file_path provided. file_path will override loader.",
                        self.abstract_broker_logger_prefix,
                    )
                self.loader = SAMLoader(file_path=file_path)
                if self._loader and self._loader.ready:
                    self.kind_setter(self._loader.manifest_kind)
                    loader_metadata = self._loader.manifest_metadata or {}
                    self.name_cached_property_setter(loader_metadata.get("name"))

        # ----------------------------------------------------------------------
        # Fallback logic to initialize from the ORM, if we have a name and
        # user_profile, and we don't already have a manifest or loader.
        # ----------------------------------------------------------------------
        if not self._manifest and not self._loader:
            self.orm_meta_instance_setter()

        # evaluated in order, and only as far as needed, because SAMLoader.ready may parse the manifest.
        if self._manifest:
            self._validated = True
        elif self._loader and self._loader.ready:
            self._validated = True
        else:
            self._validated = bool(self._orm_instance)

        # ----------------------------------------------------------------------
        # log initialization state.
        # ----------------------------------------------------------------------
        self.log_abstract_broker_state()

    def __str__(self) -> str:
        """
        Returns the string representation of the broker, naming its concrete class.

        example: ``SAMLLMClientBroker[id=140234](name=my-llmclient, user_profile=Acme-jane@acme.com)``

        :return: The string representation of the broker.
        """
        user_profile = self.user_profile or "Anonymous"
        name = self.known_name or "Unknown"

        return f"{self.__class__.__name__}[id={id(self)}](name={name}, user_profile={user_profile})"

    def __repr__(self) -> str:
        """
        Returns the developer representation of the broker, which is the same as :meth:`__str__`.

        :return: The developer representation of the broker.
        """
        return self.__str__()

    def __bool__(self) -> bool:
        """
        Return True if the broker is ready for operations.

        :return: True if the broker is ready for operations.
        """
        return self.ready

    def __hash__(self) -> int:
        """
        Return the hash of the broker based on account, kind, and name.

        :return: The hash of the broker.
        """
        return hash((self.account, self.kind, self.name))

    def __eq__(self, other: object) -> bool:
        """
        Check if two brokers are equal based on account, kind, and name.

        :param other: The other broker to compare.
        :return: True if the brokers are equal, or ``NotImplemented`` if
            ``other`` is not an :class:`AbstractBroker`.
        """
        if not isinstance(other, AbstractBroker):
            return NotImplemented
        return self.account == other.account and self.kind == other.kind and self.name == other.name

    ###########################################################################
    # Class Instance Properties
    ###########################################################################
    @cached_property
    def abstract_broker_logger_cache_invalidation_prefix(self) -> str:
        """Return the logger prefix for the AbstractBroker cache invalidation.

        It is built once per broker: every log message starts with it.

        :return: The logger prefix for the AbstractBroker.
        """
        prefix = f"{__name__}.{AbstractBroker.__name__}[{id(self)}]"
        return self.formatted_text_blue(prefix)

    @cached_property
    def abstract_broker_logger_prefix(self) -> str:
        """Return the logger prefix for the AbstractBroker.

        It is built once per broker: every log message starts with it.

        :return: The logger prefix for the AbstractBroker.
        """
        class_name = f"{__name__}.{AbstractBroker.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    # a property, not SmarterHelperMixin's classproperty, so that the prefix has the instance's id.
    @property
    def formatted_class_name(self) -> str:  # type: ignore[override]  # pylint: disable=arguments-renamed
        """Return the logger prefix for the AbstractBroker.

        :return: The logger prefix for the AbstractBroker.
        """
        return self.abstract_broker_logger_prefix

    @property
    def formatted_class_name_cache_invalidations(self) -> str:
        """Return the logger prefix for the AbstractBroker cache invalidations.

        :return: The logger prefix for the AbstractBroker cache invalidations.
        """
        return self.abstract_broker_logger_cache_invalidation_prefix

    @property
    def is_ready_abstract_broker(self) -> bool:
        """Return True if the AbstractBroker is ready for operations.

        An AbstractBroker is considered ready, and stays ready, if any of these is true:

        - The request is for an example manifest.
        - The request is for a JSON schema.
        - A manifest is loaded.
        - A ready SAMLoader is present.
        - An ORM meta instance was found.

        Every reason why a broker is not ready is logged at DEBUG. A broker that is not ready is
        normal for a command that needs no single resource, e.g. ``get`` (a list). A command that
        does need one fails with :class:`SAMBrokerErrorNotReady`, which the cli view logs.

        :return: True if the AbstractBroker is ready for operations.
        """
        if self._is_ready_abstract_broker:
            return self._is_ready_abstract_broker

        # ---------------------------------------------------------------------
        # there are five possible ways for us to be ready.
        # ---------------------------------------------------------------------
        if self.request and "example-manifest" in self.request.path:
            # 1.) if the request path indicates this is an example-manifest operation
            self._is_ready_abstract_broker = True
            return self._is_ready_abstract_broker
        if self.request and "json-schema" in self.request.path:
            # 2.) if the request path indicates this is a json-schema operation
            self._is_ready_abstract_broker = True
            return self._is_ready_abstract_broker
        if bool(self._manifest):
            # 3.) if we have a manifest.
            self._is_ready_abstract_broker = True
        if self.loader is not None and self.loader.ready:
            # 4.) we have a loader and it's in a ready state.
            self._is_ready_abstract_broker = True
        if bool(self.orm_meta_instance):
            # 5.) we have an ORM meta instance.
            self._is_ready_abstract_broker = True

        if self._is_ready_abstract_broker:
            return self._is_ready_abstract_broker

        # ---------------------------------------------------------------------
        # log every reason why we are not ready.
        # ---------------------------------------------------------------------
        if not self._name:
            logger.debug(
                "%s.is_ready_abstract_broker() - Broker name is not set. Cannot process broker.",
                self.abstract_broker_logger_prefix,
            )
        if not self.srm_ready:
            logger.debug(
                "%s.is_ready_abstract_broker() - SmarterRequestMixin is not ready. Cannot process broker.",
                self.abstract_broker_logger_prefix,
            )
        if not bool(self._manifest):
            logger.debug(
                "%s.is_ready_abstract_broker() returning false because manifest is not loaded.",
                self.abstract_broker_logger_prefix,
            )
        if self.loader is None or not self.loader.ready:
            logger.debug(
                "%s.is_ready_abstract_broker() returning false because loader is not ready.",
                self.abstract_broker_logger_prefix,
            )

        return self._is_ready_abstract_broker

    @property
    def abstract_broker_ready_state(self) -> str:
        """Return a string representation of the AbstractBroker's ready state.

        :return: "READY" if the AbstractBroker is ready, otherwise "NOT_READY".
        """
        if self.is_ready_abstract_broker:
            return self.formatted_state_ready
        return self.formatted_state_not_ready

    @property
    def ready(self) -> bool:
        """Return True if the broker is ready for operations.

        A broker is considered ready if it has a valid manifest loaded.

        :return: True if the broker is ready for operations.
        """
        if self._ready:
            return self._ready
        retval = super().ready
        if not retval:
            logger.warning(
                "%s.ready() SmarterRequestMixin is not ready for kind=%s",
                self.abstract_broker_logger_prefix,
                self.kind,
            )
            return False
        self._ready = retval and self.is_ready_abstract_broker
        return self._ready

    @property
    def ready_state(self) -> str:
        """Return a string representation of the broker's ready state.

        :return: "READY" if the broker is ready, otherwise "NOT_READY".
        """
        if self.ready:
            return self.formatted_state_ready
        return self.formatted_state_not_ready

    @property
    def request(self) -> Optional[HttpRequest]:
        """Return the request object.

        :return: The request object.
        """
        return self.smarter_request

    # a property, not SmarterRequestMixin's cached_property, because it also reads a PreparedRequest.
    @property
    def params(self) -> Optional[QueryDict]:  # type: ignore[override]
        """
        Return the query parameters from the url of the request.

        There are two scenarios to consider:

        1. the request is a Django HttpRequest object (the expected case)
        2. the request is a Python PreparedRequest object (the edge case)

        :return: The query parameters from the url of the request.
        """
        if isinstance(self.request, PreparedRequest):
            query = urlparse(self.request.url).query
            if not query:
                return QueryDict("", mutable=True)
            if isinstance(query, memoryview):
                query = query.tobytes().decode("utf-8")
            elif isinstance(query, (bytes, bytearray)):
                query = query.decode("utf-8")
            query_params = parse_qs(query)
            flat_params = {k: v[0] for k, v in query_params.items()}
            qd = QueryDict("", mutable=True)
            qd.update(flat_params)
            return qd
        if self.request:
            return self.request.GET
        return QueryDict("", mutable=True)

    @property
    def uri(self) -> Optional[str]:
        """Return the full uri of the request.

        :return: The full uri of the request.
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
        """
        return self._created

    @property
    def is_valid(self) -> bool:
        """
        True if the broker has a manifest, a ready loader, or an ORM instance.

        :returns: Whether the broker was initialized from any of them.
        """
        return self._validated

    @property
    def thing(self) -> SmarterJournalThings:
        """
        The Smarter Journal Thing for this broker.

        :return: The Smarter Journal Thing for this broker.
        """
        if not self._thing:
            self._thing = SmarterJournalThings(self.kind)
        return self._thing

    @property
    def kind(self) -> Optional[str]:
        """
        The kind of manifest.

        :return: The kind of manifest.
        """
        return self._kind

    def kind_setter(self, value: Optional[str]) -> None:
        """
        Set the kind of manifest.

        Validates that the kind is a valid SmarterJournalThings value. None is ignored, with a
        warning, because a kind cannot be unset.

        :param value: The kind of manifest to set.
        :raises SmarterValueError: If the kind is not valid.
        """
        if value is None:
            logger.warning(
                "%s.kind_setter() - cannot unset kind. Ignoring this operation.",
                self.abstract_broker_logger_prefix,
            )
            return
        if not isinstance(value, str):
            raise SmarterValueError(f"kind must be a string. Got: {type(value)} {value}")
        if value not in KNOWN_KINDS:
            raise SmarterValueError(
                f"kind '{value}' is not a valid SmarterJournalThings value. Expected one of: {SmarterJournalThings.all()}"
            )

        self._kind = value

    @property
    def name(self) -> Optional[str]:
        """
        The name of the resource that this broker manages, its manifest's ``metadata.name``.

        The name is looked up once, and kept: from the manifest, if it is a Pydantic model, else
        from the loader's manifest metadata, else from the request's ``name`` query parameter. A
        name that cannot be found is logged at debug level, since some commands, e.g.
        ``json-schema``, need no name, and those that do fail with their own error.

        The name is essential for database queries and model lookups, together with the user profile.

        :returns: The name of the resource, or ``None`` if the name is not set or cannot be determined.

        .. note::

            The name property is a critical identifier used throughout the broker to ensure correct
            mapping between manifest data and persistent application state.
        """
        if self._name:
            return self._name
        if isinstance(self._manifest, AbstractSAMBase) and self._manifest.metadata and self._manifest.metadata.name:
            self._name = self._manifest.metadata.name
            return self._name
        if self._loader:
            loader_metadata = self._loader.manifest_metadata or {}
            self._name = loader_metadata.get("name")
            if self._name:
                return self._name
            logger.warning("%s.name() loader metadata does not contain a name", self.abstract_broker_logger_prefix)
        params = self.params
        if isinstance(params, QueryDict):
            name_param = params.get("name", None)
            if name_param:
                self._name = name_param
        if not self._name:
            # debug, not warning: commands such as json-schema need no name, and the commands
            # that do (get, describe, delete, ...) fail with their own error (issue #952).
            logger.debug("%s.name() unable to lazily set name.", self.abstract_broker_logger_prefix)
        return self._name

    def manifest_to_django_orm(self) -> SmarterDictType:
        """
        Convert the Smarter API manifest metadata into a dictionary for creating or updating the resource's Django ORM model.

        This method extracts all relevant metadata from the loaded manifest
        and transforms it into a dictionary format compatible with Django ORM operations. The manifest's configuration
        is first dumped and converted from camelCase to snake_case to match Django's field naming conventions.

        The resulting dictionary includes the account, name, description, and version fields from the manifest metadata.
        This dictionary is intended to be used to supplement the model spec when instantiating or updating the ORM model instance in the database.

        If the manifest is not loaded or is invalid, an exception is raised to indicate that the broker is not ready
        to perform the transformation.

        :returns: A dictionary containing the user profile and all metadata fields, to create or update the Django ORM model.

        :raises SAMBrokerErrorNotReady: If the manifest is not loaded, or the broker has no user profile.
        :raises SAMBrokerError: If the manifest metadata cannot be converted to a dictionary.
        """
        if not isinstance(self.manifest, AbstractSAMBase):
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind)
        if self.user_profile is None:
            raise SAMBrokerErrorNotReady(
                message="No user profile set for the broker",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )
        metadata = self.manifest.metadata.model_dump()
        # annotation keys are user data, such as "smarter.sh/created-by", so they keep their case.
        has_annotations = "annotations" in metadata
        annotations = metadata.pop("annotations", None)
        metadata = self.to_snake_case(metadata)
        if has_annotations and isinstance(metadata, dict):
            metadata["annotations"] = annotations
        if not isinstance(metadata, dict):
            raise SAMBrokerError(
                message=f"Manifest metadata could not be converted to a dictionary. Expected a dictionary after to_snake_case transformation, but got {type(metadata)}",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )
        retval = {
            "user_profile": self.user_profile,
            **metadata,
        }

        return retval

    def name_cached_property_setter(self, value: Optional[str]) -> None:
        """
        Set the broker's name, which :attr:`name` then returns.

        :attr:`name` was once a ``cached_property``, so this also deletes a cached value of it from
        the instance's ``__dict__``, if one is there.

        :param value: The name to set for the manifest, or None.
        :raises SmarterValueError: If the value is neither a string nor None.
        """
        if type(value) not in [str, type(None)]:
            raise SmarterValueError("name must be a string or None")

        self._name = value
        # Delete cached_property value if present
        try:
            del self.__dict__["name"]  # type: ignore
        except KeyError:
            pass

    @property
    def api_version(self) -> str:
        """
        The API version of the manifest.

        :return: The API version of the manifest.
        """
        return self._api_version

    @api_version.setter
    def api_version(self, value: str) -> None:
        """
        Set the API version of the manifest.

        :param value: The API version to set.
        """
        if not isinstance(value, str):
            raise SmarterValueError("api_version must be a string")
        self._api_version = value

    @property
    def loader(self) -> Optional[SAMLoader]:
        """
        The SAMLoader instance for this broker.

        :return: The SAMLoader instance for this broker.
        """
        if isinstance(self._loader, SAMLoader) and self._loader.ready:
            return self._loader
        if self._loader:
            logger.warning(
                "%s.loader() getter - loader is set but is not in a ready state.",
                self.abstract_broker_logger_prefix,
            )

        return None

    @loader.setter
    def loader(self, value: Optional[SAMLoader]) -> None:
        """
        Set the SAMLoader instance for this broker.

        :param value: The SAMLoader instance to set.
        """
        if not value:
            self._loader = None
            return
        if not isinstance(value, SAMLoader):
            raise SmarterValueError("loader must be a SAMLoader instance")
        if value.manifest_kind != self.kind:
            raise SAMBrokerError(
                f"loader manifest kind '{value.manifest_kind}' does not match broker kind '{self.kind}'"
            )
        self.raise_for_unknown_keys(value.json_data)
        self._loader = value

    def raise_for_unknown_keys(self, manifest: object) -> None:
        """
        Raise a validation error if the manifest has keys that its Pydantic model does not define.

        The models ignore such keys, so that a misspelled key, e.g. ``defaultTemperatura``, would
        otherwise be silently ignored, rather than be reported to the client as an error.

        :param manifest: The manifest, as a dict. Anything else is not checked, nor is a manifest of a
            broker whose Pydantic model is :class:`~smarter.lib.manifest.models.AbstractSAMBase` itself.
        :raises SAMValidationError: If the manifest has keys that its Pydantic model does not define.
        """
        if not isinstance(manifest, dict):
            return
        model = self._pydantic_model
        if not issubclass(model, AbstractSAMBase):
            return
        if model is AbstractSAMBase:
            return
        unknown = unknown_keys(model, manifest)
        if unknown:
            raise SAMValidationError(
                f"The {self.kind} manifest has keys that it does not define: {', '.join(unknown)}. "
                "Check their spelling, or remove them."
            )

    ###########################################################################
    # Abstract Properties
    ###########################################################################
    @property
    @abstractmethod
    def SerializerClass(self) -> Type[ModelSerializer]:
        """
        Return the serializer class for the broker.

        :return: The serializer class definition for the broker.
        """
        raise SAMBrokerErrorNotImplemented(message="", thing=self.thing, command=None)

    @property
    @abstractmethod
    def ORMMetaModelClass(self) -> Type[MetaModelT]:
        """
        Return the Django ORM meta model class for the broker.

        :return: The Django ORM meta model class definition for the broker.
        """
        raise SAMBrokerErrorNotImplemented(
            message="Subclasses must implement the MetaModelClass", thing=self.thing, command=None
        )

    @property
    @abstractmethod
    def ORMModelClass(self) -> Type[ModelT]:
        """
        Return the Django ORM model class for the broker.

        :return: The Django ORM model class definition for the broker.
        """
        raise SAMBrokerErrorNotImplemented(
            message="Subclasses must implement the ModelClass", thing=self.thing, command=None
        )

    @property
    def orm_meta_instance(self) -> Optional[MetaModelT]:
        """
        Return the Django ORM meta model instance for the broker.

        It is the instance that :meth:`orm_meta_instance_setter` found, by the broker's name and
        user profile, or None. For simple relational models, the ORM meta class is the same
        as the ORM class, and the meta instance is the same as the ORM instance.

        This property is used for resolving more complex ORM relationships where
        the name and user_profile fields are stored in a parent Django model.
        """
        return self._orm_meta_instance

    def orm_meta_instance_setter(self) -> None:
        """
        Initialize the ORM metadata for the broker instance.

        This method attempts to initialize the ORM metadata by querying the
        ORMMetaModelClass using the broker's name and user_profile, then the account admin's
        user profile, then the Smarter admin's. If the ORM metadata is successfully retrieved,
        it is stored in the ``_orm_meta_instance`` attribute. If none is found, or an error occurs,
        ``_orm_meta_instance`` stays None. Multiple matches and unexpected errors are logged.

        Nothing is done without a name and a user profile. If the meta model class is the ORM
        model class, and the ORM instance is already known, it is used instead of a query.
        """
        if not self._name or not self._user_profile:
            return
        orm_instance = self._orm_instance
        same_model_class = self.ORMMetaModelClass == self.ORMModelClass
        if same_model_class and isinstance(orm_instance, self.ORMMetaModelClass):
            self._orm_meta_instance = orm_instance
            return

        meta_model_class = self.ORMMetaModelClass
        if not issubclass(meta_model_class, MetaDataModel):
            raise SAMBrokerErrorNotImplemented(
                message=f"{meta_model_class.__name__} is not a MetaDataModel, so {self.__class__.__name__} must override orm_meta_instance_setter()",
                thing=self.thing,
                command=None,
            )
        self._orm_meta_instance = self.get_owned_object(meta_model_class, "orm_meta_instance_setter")

    def owner_user_profiles(self) -> Iterator[Optional[UserProfile]]:
        """
        Yield the user profiles that may own the broker's resource, in the order they are tried.

        They are the broker's user profile, the account admin's, and the Smarter admin's. Each one is
        looked up only when the one before it didn't own the resource.

        :returns: An iterator of the user profiles.
        """
        yield self.user_profile
        account_admin_user = get_cached_admin_user_for_account(account=self.account)  # type: ignore
        account_admin_user_profile = UserProfile.get_cached_object(user=account_admin_user)  # type: ignore
        yield account_admin_user_profile
        yield smarter_cached_objects.smarter_admin_user_profile

    def get_owned_object(self, model_class: Type[OwnedModelT], caller: str) -> Optional[OwnedModelT]:
        """
        Return the row of ``model_class`` that has the broker's name, owned by the first owner that has one.

        The owners are tried in the order of :meth:`owner_user_profiles`. A row that isn't found is
        expected, e.g. for a manifest applied for the first time. Several rows for one owner, or an
        unexpected error, are logged, and end the search.

        :param model_class: The model to look the row up in.
        :param caller: The calling method's name, for log messages.
        :returns: The row, or None.
        """
        for user_profile in self.owner_user_profiles():
            try:
                owned_object = model_class.get_cached_object(name=self.name, user_profile=user_profile)
                # get_cached_object() is annotated as returning models.Model, but returns a row of
                # the class it is called on.
                return cast(OwnedModelT, owned_object)
            except model_class.MultipleObjectsReturned:
                logger.error(
                    "%s.%s() - Multiple %s instances found for name '%s' and user_profile '%s'. Cannot determine which one to use.",
                    self.abstract_broker_logger_prefix,
                    caller,
                    model_class.__name__,
                    self.name,
                    user_profile,
                )
                return None
            except model_class.DoesNotExist:
                continue
            # pylint: disable=broad-except
            except Exception as e:
                logger.error(
                    "%s.%s() - unexpected error retrieving %s for %s owned by %s: %s",
                    self.abstract_broker_logger_prefix,
                    caller,
                    model_class.__name__,
                    self.name,
                    user_profile,
                    e,
                    exc_info=True,
                )
                return None
        return None

    @property
    def orm_instance(self) -> Optional[ModelT]:
        """
        Return the Django ORM model instance for the broker.

        There are
        multiple strategies to retrieve the ORM instance:

        1. If the instance is already cached in self._orm_instance, return it.
        2. If the broker is not ready or the name is not set, log a warning and return None.
        3. Attempt to retrieve the ORM instance using the user_profile and name.
           If not found, attempt to retrieve using the admin user_profile for the account.
           If still not found, attempt to retrieve using the Smarter platform admin user_profile.
        4. Cache the retrieved instance for future access.

        :return: The Django ORM model instance for the broker.
        """
        if self._orm_instance:
            return self._orm_instance

        # this should work in any cases where orm_instance() is not overridden
        # by a subclass. The meta instance is the ORM instance only when both
        # are of the same model, e.g. not a plugin's PluginMeta.
        orm_meta_instance = self.orm_meta_instance
        if isinstance(orm_meta_instance, self.ORMModelClass):
            self._orm_instance = orm_meta_instance
            return self._orm_instance

        if not self.name:
            return None
        if not self.user_profile:
            return None

        model_class = self.ORMModelClass
        if not issubclass(model_class, MetaDataModel):
            raise SAMBrokerErrorNotImplemented(
                message=f"{model_class.__name__} is not a MetaDataModel, so {self.__class__.__name__} must override orm_instance",
                thing=self.thing,
                command=None,
            )
        orm_instance = self.get_owned_object(model_class, "orm_instance")
        self._orm_instance = orm_instance
        if orm_instance is None:
            return None
        if isinstance(orm_instance, self.ORMMetaModelClass):
            self._orm_meta_instance = orm_instance
        else:
            self.orm_meta_instance_setter()

        return self._orm_instance

    @property
    def SAMModelClass(self) -> Type[AbstractSAMBase]:
        """
        Return the SAM (Smarter Api Manifest) model class for the broker.

        :return: The Pydantic model class definition for the broker.
        """
        return self._pydantic_model

    @property
    @abstractmethod
    def manifest(self) -> Optional[Union[AbstractSAMBase, SmarterDictType]]:
        """
        The Pydantic model representing the manifest.

        If the manifest
        has not been initialized yet, this property will attempt to
        initialize it using the SAMLoader.

        :return: The Pydantic model representing the manifest.
        """
        raise SAMBrokerErrorNotImplemented("Subclasses must implement the manifest property.")

    def manifest_setter(self, value: Optional[Union[AbstractSAMBase, SmarterDictType]]) -> None:
        """
        Set the manifest for the broker and override all AbstractBroker model properties based on the manifest data.

        :param value: The manifest to set, either as a Pydantic model or a dictionary.
        """
        if value is None:
            self._manifest = None
            return
        if isinstance(value, AbstractSAMBase):
            self._manifest = value
            self._api_version = self._manifest.apiVersion
            self.name_cached_property_setter(self._manifest.metadata.name)
            self.kind_setter(self._manifest.kind)
            self.loader = SAMLoader(manifest=self._manifest.model_dump())
        elif isinstance(value, dict):
            self.loader = SAMLoader(manifest=value)
            if not isinstance(self._loader, SAMLoader):
                raise SmarterValueError("loader must be a SAMLoader instance after setting manifest from dict")
            if not (self._loader.ready and self.manifest):
                logger.warning(
                    "%s.manifest_setter() - manifest is not ready after lazy load attempt from SAMLoader. Loader ready: %s, manifest initialized: %s",
                    self.abstract_broker_logger_prefix,
                    self._loader.ready,
                    self.ready,
                )
            if not self._loader.ready:
                raise SmarterValueError("cannot set manifest from dict: SAMLoader could not load manifest")
            if self._loader.kind != self.kind:
                raise SmarterValueError(
                    f"cannot set manifest from dict: manifest kind '{self._loader.kind}' does not match broker kind '{self.kind}'"
                )
            if self.api_version != self._loader.api_version:
                raise SmarterValueError(
                    f"cannot set manifest from dict: manifest apiVersion '{self._loader.api_version}' does not match broker apiVersion '{self.api_version}'"
                )
            if not isinstance(self._loader.json_data, dict):
                raise SmarterValueError("cannot set manifest from dict: loader json_data is not a dict")

        if self._manifest:
            self._validated = True
            self._created = True
        else:
            self._validated = False
            self._created = False
            logger.warning(
                "%s.manifest_setter() - manifest is not set after attempt to set it. validated and created flags set to False.",
                self.abstract_broker_logger_prefix,
            )

    @property
    def known_name(self) -> Optional[str]:
        """
        The broker's name, as far as it is known without building its manifest.

        Readiness messages are logged while a broker initializes, after its loader has read the
        manifest's name but before :attr:`name` is set. This keeps them from reporting no name.

        :returns: The name, from the broker, its manifest or its loader, or None.
        """
        if self._name:
            return self._name
        if isinstance(self._manifest, AbstractSAMBase) and self._manifest.metadata and self._manifest.metadata.name:
            return self._manifest.metadata.name
        if self._loader and self._loader.manifest_metadata:
            return self._loader.manifest_metadata.get(SAMMetadataKeys.NAME.value)
        return None

    def send_broker_ready(self, signal: Signal) -> None:
        """
        Send a ``broker_ready`` signal, once per broker.

        Brokers send it from their ``ready`` property, which is read many times while a manifest
        is applied. Each send was logged, so one apply logged that its broker was ready four to six
        times.

        :param signal: The app's ``broker_ready`` signal.
        :returns: None
        """
        if self._broker_ready_sent:
            return
        self._broker_ready_sent = True
        signal.send(sender=self.__class__, broker=self)

    @staticmethod
    def assign_changed_fields(instance: models.Model, data: SmarterDictType) -> list[str]:
        """
        Set the fields of an ORM instance whose values differ from the manifest's.

        A broker's ``apply()`` saves the instance only when this returns a field. See
        :func:`smarter.lib.django.models.utils.assign_changed_fields`.

        :param instance: The ORM instance.
        :param data: The fields from the manifest, from ``manifest_to_django_orm()``.
        :returns: The names of the fields that were set, because their values changed.
        """
        return assign_changed_fields(instance, data)

    @staticmethod
    def tags_changed(instance: models.Model, tags: list[str]) -> bool:
        """
        Whether the tags of an ORM instance differ from the manifest's.

        See :func:`smarter.lib.django.models.utils.tags_changed`.

        :param instance: The ORM instance, which has a ``tags`` TaggableManager.
        :param tags: The manifest's tags.
        :returns: True if the instance is new, or its tags differ.
        """
        return tags_changed(instance, tags)

    ###########################################################################
    # Abstract Methods
    ###########################################################################
    def cache_invalidations(self) -> None:
        """Handle broker specific cache invalidation logic."""

        # This should be the very last thing that happens. This Django
        # signal will potentially trigger a wide variety of cache invalidations
        # in outer concentric layers of the application, so we want to ensure
        # that all SAM resources have already invalidated in order to avoid
        # unpredictable downstream behavior.
        cache_invalidate.send(sender=self.__class__, user_profile=self.user_profile)

    @abstractmethod
    def apply(self, request: HttpRequest, *args, **kwargs) -> Optional[SmarterJournaledJsonResponse]:
        """
        Apply a manifest, which works like an upsert operation.

        This abstract method should be implemented by subclasses to provide
        the logic for applying a manifest to create or update a resource.

        Designed
        around the Kubernetes ``kubectl apply`` command.

        This method processes a Smarter YAML manifest and either creates or updates
        the corresponding resource, depending on whether it already exists.

        Example manifest metadata::

            metadata:
                description: new description
                name: test71d12b8212b628df
                version: 1.0.0

        :param request: The HTTP request object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A SmarterJournaledJsonResponse if implemented, otherwise None.
        """
        raise SAMBrokerErrorNotImplemented(
            message="apply() not implemented", thing=self.thing, command=SmarterJournalCliCommands.APPLY
        )

    @abstractmethod
    def prompt(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Invoke a prompt operation.

        This abstract method should be implemented by subclasses to provide
        prompt-based interactions with the broker resource.

        :param request: The HTTP request object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A SmarterJournaledJsonResponse containing the prompt response.
        """
        raise SAMBrokerErrorNotImplemented(
            message="prompt() not implemented", thing=self.thing, command=SmarterJournalCliCommands.PROMPT
        )

    @abstractmethod
    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Describe a resource.

        :param request: The HTTP request object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A SmarterJournaledJsonResponse containing the description of the resource.
        """
        raise SAMBrokerErrorNotImplemented(
            message="describe() not implemented", thing=self.thing, command=SmarterJournalCliCommands.DESCRIBE
        )

    @abstractmethod
    def dependencies(self) -> List[SAMDependency]:
        """Return brokers for the resources that depend on this resource.

        A resource depends on this resource when it refers to it, so that deleting this resource
        would break it, or would delete it too. For example, an LLMClient that lists a Guardrail
        in its ``spec.guardrails`` depends on that Guardrail. The dependents are queried from the
        Django ORM, and may belong to other users. :meth:`verify_no_dependencies` uses them to
        refuse to delete a resource that is still in use.

        A broker usually implements it as ``return self.dependency_brokers_for(<its ORM instance>)``,
        so that it agrees with :meth:`dependents`, which says which resources those are.

        Example:

        .. code-block:: python

            broker = SAMGuardrailBroker(request=request, name="stupid_input", kind="Guardrail")
            for dependency in broker.dependencies():
                print(dependency.kind, dependency.name)
            # LLMClient smarter_example

        :return: A broker for each resource that depends on this resource, or an empty list. See
            :meth:`dependency_broker` for the :class:`SAMDependencyReference` it returns in place of a
            broker that fails to initialize.
        """
        raise SAMBrokerErrorNotImplemented(message="dependencies() not implemented", thing=self.thing)

    @classmethod
    def dependents(cls, instance: MetaModelT) -> SAMDependents:
        """Return the resources that depend on a resource, as Django ORM rows, without building brokers.

        This is the one place where a broker says which resources refer to its kind of resource.
        :meth:`dependencies` builds a broker for each of these rows, and :meth:`has_dependents`
        only asks whether there are any, which is much cheaper: a resource list page asks it for
        every row that it shows, as that row's ``canDelete``.

        Return lazy QuerySets where possible, so that :meth:`has_dependents` can ask each with
        one ``EXISTS`` query. Rows that can only be filtered in Python may be a generator.

        Example:

        .. code-block:: python

            @classmethod
            def dependents(cls, instance: Guardrail) -> SAMDependents:
                llmclients = LLMClient.objects.filter(
                    id__in=LLMClientGuardrails.objects.filter(guardrail=instance).values("llmclient_id")
                )
                return [(SAMKinds.LLM_CLIENT.value, llmclients)]

        :param instance: The resource's Django ORM instance, e.g. a Guardrail.
        :return: The kinds and rows of the resources that depend on it, or an empty list.
        :raises SAMBrokerErrorNotImplemented: If the broker does not implement it.
        """
        raise SAMBrokerErrorNotImplemented(message=f"{cls.__name__}.dependents() not implemented")

    @classmethod
    def has_dependents(cls, instance: MetaModelT) -> bool:
        """Return True if any resource depends on a resource.

        It asks :meth:`dependents` whether there is at least one row, one kind at a time, and
        stops at the first. It builds no brokers, so it costs a few ``EXISTS`` queries.

        Example:

        .. code-block:: python

            if SAMGuardrailBroker.has_dependents(guardrail):
                print("an LLMClient uses this guardrail")

        :param instance: The resource's Django ORM instance, e.g. a Guardrail.
        :return: Whether any resource depends on it.
        :raises SAMBrokerErrorNotImplemented: If the broker does not implement :meth:`dependents`.
        """
        for _, rows in cls.dependents(instance):
            if dependents_exist(rows):
                return True
        return False

    @classmethod
    def references(cls, instance: MetaModelT) -> SAMDependents:
        """Return the resources that a resource uses, as Django ORM rows: the opposite of :meth:`dependents`.

        A resource uses another when it refers to it, by name in its manifest or by a foreign key,
        e.g. an LLMClient uses the Guardrails in its ``spec.guardrails``, and an SqlConnection uses
        the Secret of its password. Each edge here is the same edge that the other kind's
        :meth:`dependents` lists, seen from this end. :meth:`dependency_tree` follows them, recursively.

        A kind of resource that uses no others returns an empty list.

        Example:

        .. code-block:: python

            @classmethod
            def references(cls, instance: MCPClient) -> SAMDependents:
                secrets = Secret.objects.filter(pk=instance.credentials_id)
                return [(SAMKinds.SECRET.value, secrets)]

        :param instance: The resource's Django ORM instance, e.g. an LLMClient.
        :return: The kinds and rows of the resources that it uses, or an empty list. A kind of None
            means that each row has its own kind, in its ``kind`` field, as a plugin's PluginMeta does.
        :raises SAMBrokerErrorNotImplemented: If the broker does not implement it.
        """
        raise SAMBrokerErrorNotImplemented(message=f"{cls.__name__}.references() not implemented")

    @property
    def dependency_tree_instance(self) -> Optional[models.Model]:
        """The Django ORM instance that is the root of :meth:`dependency_tree`, and that :meth:`references` takes.

        It is :attr:`orm_instance`, unless a broker's ORM instance is not the row that the other kinds
        refer to, e.g. a plugin's, whose rows are referred to by their PluginMeta.

        :return: The instance, or None if the resource does not exist.
        """
        return self.orm_instance

    def dependency_tree(self) -> Optional[SAMDependencyTreeNode]:
        """Return the tree of every resource that this resource uses, recursively, by record locator.

        The root is this resource. Its children are the resources that it uses, as :meth:`references`
        lists them, and theirs are the resources that they use, down to the resources that use no
        others, such as Secrets. A resource that two others use is in the tree twice, once under each.
        A resource that is already one of its own ancestors is a leaf, so that a cycle ends.

        Each node has the kind's icon, from :func:`smarter.apps.api.v1.manifests.enum.sam_kind_icon`, the
        resource's owner, its record locator, and the path of its manifest page in the web console, derived
        from the record locator by :func:`smarter.lib.manifest.record_locator.console_url`, and the url of
        its detail, by :func:`smarter.apps.dashboard.resource_detail.resource_detail_url`, so that a web
        console page can draw the tree with a card for each resource. A resource that the authenticated user may not read has only
        its kind and record locator, and no children.

        Example:

        .. code-block:: python

            broker = SAMLLMClientBroker(request=request, name="stackademy_sql", kind="LLMClient")
            tree = broker.dependency_tree()
            tree.model_dump(mode="json")
            # {"kind": "LLMClient", "icon": "artificial-intelligence", "name": "stackademy_sql",
            #  "owner": "Ada Lovelace (ada)",
            #  "recordLocator": "llmclient-rMTAwMDAxMwx",
            #  "url": "/workbench/llm-clients/rMTAwMDAxMwx/manifest/", "readable": True,
            #  "children": [{"kind": "SqlPlugin", "name": "stackademy_sql", ...,
            #                "children": [{"kind": "SqlConnection", ..., "children": [{"kind": "Secret", ...}]}]}]}

        :return: The tree, or None if the resource does not exist.
        :raises SAMBrokerErrorNotImplemented: If a broker in the tree does not implement :meth:`references`.
        """
        instance = self.dependency_tree_instance
        if instance is None:
            return None
        return self.dependency_tree_node(str(self.kind), instance, ancestors=frozenset())

    def dependency_tree_node(
        self,
        kind: str,
        instance: models.Model,
        ancestors: frozenset[Optional[str]],
        recursive: bool = True,
        readable: Optional[bool] = None,
    ) -> SAMDependencyTreeNode:
        """Return one resource's node of :meth:`dependency_tree`, with the nodes of the resources that it uses.

        :param kind: The SAM kind of the resource, e.g. ``SAMKinds.LLM_CLIENT.value``.
        :param instance: The resource's Django ORM instance.
        :param ancestors: The record locators of the resource's ancestors in the tree.
        :param recursive: Whether the node has the nodes of the resources that it uses. A node without them
            describes the resource alone, e.g. one of the resources that depend on another, in a list.
        :param readable: Whether the authenticated user may read the resource, when the caller already
            knows, e.g. for a whole group of siblings at once. None checks it with :meth:`dependency_tree_readable`.
        :return: The node.
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.api.v1.cli.brokers import Brokers
        from smarter.apps.api.v1.manifests.enum import sam_kind_icon
        from smarter.apps.dashboard.resource_detail import resource_detail_url

        record_locator: Optional[str] = getattr(instance, "record_locator", None)
        icon = sam_kind_icon(kind)
        if readable is None:
            readable = self.dependency_tree_readable(instance)
        if not readable:
            return SAMDependencyTreeNode(kind=kind, icon=icon, recordLocator=record_locator, readable=False)
        children: List[SAMDependencyTreeNode] = []
        broker_class = Brokers.get_broker(kind)
        if recursive and broker_class is not None and record_locator not in ancestors:
            path = ancestors | {record_locator}
            for child_kind, rows in broker_class.references(instance):
                rows_with_owners = self.with_owners(rows)
                unique = {row.pk: row for row in rows_with_owners}
                siblings = list(unique.values())
                readable_pks = self.dependency_tree_readable_pks(siblings)
                for row in siblings:
                    row_kind = child_kind
                    if not row_kind:
                        # each row has its own kind, e.g. a plugin's PluginMeta.
                        row_kind = str(getattr(row.kind, "value", row.kind))  # type: ignore[attr-defined]
                    row_readable = None
                    if readable_pks is not None:
                        row_readable = row.pk in readable_pks
                    child = self.dependency_tree_node(row_kind, row, path, readable=row_readable)
                    children.append(child)
        return SAMDependencyTreeNode(
            kind=kind,
            icon=icon,
            name=self.dependency_tree_name(instance),
            owner=self.dependency_tree_owner(instance),
            recordLocator=record_locator,
            url=console_url(record_locator),
            detailUrl=resource_detail_url(kind, record_locator),
            children=sorted(children, key=lambda node: (node.kind, node.name or "")),
        )

    @staticmethod
    def dependency_tree_name(instance: models.Model) -> Optional[str]:
        """Return a resource's name in :meth:`dependency_tree`.

        It is the resource's ``name``. An Extension, which has no name, has its slug, e.g. ``weather``,
        which is how its manifest and the extension registry identify it.

        :param instance: The resource's Django ORM instance.
        :return: The name, or None if the resource has neither a name nor a slug.
        """
        name = getattr(instance, "name", None)
        if name:
            return name
        slug = getattr(instance, "slug", None)
        if slug:
            return slug
        return None

    @staticmethod
    def dependency_tree_owner(instance: models.Model) -> Optional[str]:
        """Return who owns a resource of :meth:`dependency_tree`, as the web console names a person.

        It is the full name and username of the user of the resource's ``user_profile``, e.g.
        ``Ada Lovelace (ada)``, or the username alone if the user has no name. An Extension, which no
        user owns, has its publisher.

        :param instance: The resource's Django ORM instance.
        :return: The owner, or None if the resource has none, e.g. a Budget.
        """
        user_profile = getattr(instance, "user_profile", None)
        user = getattr(user_profile, "user", None)
        if user is None:
            publisher = getattr(instance, "publisher", None)
            if publisher:
                return str(publisher)
            return None
        full_name = user.get_full_name()
        if full_name:
            return f"{full_name} ({user.username})"
        return user.username

    @staticmethod
    def with_owners(rows: Iterable[models.Model]) -> Iterable[models.Model]:
        """
        Return the rows with their owners' user profiles and users, read in the same query.

        :meth:`dependency_tree_owner` reads each row's ``user_profile.user``, which would otherwise
        be two more queries per node.

        :param rows: The rows, usually a QuerySet.
        :returns: The QuerySet with ``select_related("user_profile__user")`` when its model has a
            ``user_profile`` foreign key, else the rows as they are.
        """
        if not isinstance(rows, models.QuerySet):
            return rows
        field_names = set()
        for field in rows.model._meta.get_fields():  # pylint: disable=protected-access
            if field.many_to_one:
                field_names.add(field.name)
        if "user_profile" not in field_names:
            return rows
        try:
            rows_with_owners = rows.select_related("user_profile__user")
        except TypeError:
            # e.g. a values() QuerySet, which can't select related rows.
            return rows
        return rows_with_owners

    def dependency_tree_readable_pks(self, rows: List[models.Model]) -> Optional[set]:
        """
        Return the primary keys of the rows that the authenticated user may read, with one query.

        :param rows: Sibling rows of :meth:`dependency_tree`.
        :returns: The readable rows' primary keys, or None when each row must be checked by
            :meth:`dependency_tree_readable`: without a user, for rows of several models, or for a
            model whose manager has no read permissions.
        """
        if self.user is None:
            return None
        if not rows:
            return None
        model_classes = set()
        for row in rows:
            model_classes.add(type(row))
        if len(model_classes) != 1:
            return None
        model_class = model_classes.pop()
        manager = model_class._default_manager  # pylint: disable=protected-access
        if not hasattr(manager, "with_read_permission_for"):
            return None
        pks = [row.pk for row in rows]
        readable_rows = manager.filter(pk__in=pks).with_read_permission_for(self.user)  # type: ignore[attr-defined]
        readable_pks = set(readable_rows.values_list("pk", flat=True))
        return readable_pks

    def dependency_tree_readable(self, instance: models.Model) -> bool:
        """Return True if the authenticated user may read a resource of :meth:`dependency_tree`.

        A resource whose manager has no read permissions, e.g. an Extension, which every account
        that has it enabled may use, is readable.

        :param instance: The resource's Django ORM instance.
        :return: Whether the user may read it.
        """
        manager = type(instance)._default_manager  # pylint: disable=protected-access
        if self.user is None:
            return True
        if not hasattr(manager, "with_read_permission_for"):
            return True
        rows = manager.filter(pk=instance.pk)
        readable = rows.with_read_permission_for(self.user).exists()  # type: ignore[attr-defined]
        return readable

    def dependency_brokers_for(self, instance: Optional[MetaModelT]) -> List[SAMDependency]:
        """Return a broker for each resource that depends on a resource, as :meth:`dependents` lists them.

        :param instance: The resource's Django ORM instance, or None if it does not exist.
        :return: A broker, or a reference, for each resource that depends on it, or an empty list
            if it does not exist. See :meth:`dependency_brokers`.
        """
        if instance is None:
            return []
        retval: List[SAMDependency] = []
        for kind, rows in self.dependents(instance):
            retval += self.dependency_brokers(kind, rows)
        return retval

    def dependency_broker(
        self,
        kind: str,
        instance: models.Model,
        name: Optional[str] = None,
        user_profile: Optional[UserProfile] = None,
    ) -> SAMDependency:
        """Return a broker for a resource that depends on this resource.

        The broker is initialized from the ORM, for the resource's own owner, which may be
        another user than this broker's. A broker can fail to initialize when the resource's
        stored data no longer validates, e.g. a plugin whose model was removed from the list of
        valid models. One broken dependent must not break the resource it depends on, so this
        returns a :class:`SAMDependencyReference` with the resource's kind, name and owner instead.

        :param kind: The SAM kind of the resource, e.g. ``SAMKinds.LLM_CLIENT.value``.
        :param instance: The resource's Django ORM instance. It has a ``user_profile``.
        :param name: The resource's manifest name. Defaults to ``instance.name``.
        :param user_profile: The resource's owner. Defaults to ``instance.user_profile``.
        :return: A broker for the resource, or a reference to it if its broker fails to initialize.
        :raises SAMBrokerInternalError: If no broker is registered for ``kind``.
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.api.v1.cli.brokers import Brokers

        broker_class = Brokers.get_broker(kind)
        if broker_class is None:
            raise SAMBrokerInternalError(f"No broker for kind {kind}", thing=self.thing)
        resource_name: str = name or getattr(instance, "name")
        user_profile = user_profile or getattr(instance, "user_profile")
        try:
            return broker_class(None, name=resource_name, kind=kind, user_profile=user_profile)
        # any error in the dependent's own data. pylint: disable=W0718
        except Exception as e:
            logger.warning(
                "%s.dependency_broker() could not initialize the broker of %s %s, which depends on %s %s: %s",
                self.abstract_broker_logger_prefix,
                kind,
                resource_name,
                self.kind,
                self.name,
                e,
            )
            return SAMDependencyReference(kind=kind, name=resource_name, user_profile=user_profile)

    def dependency_brokers(self, kind: Optional[str], instances: Iterable[models.Model]) -> List[SAMDependency]:
        """Return a broker for each resource that depends on this resource.

        :param kind: The SAM kind of the resources, e.g. ``SAMKinds.LLM_CLIENT.value``, or None if
            each resource has its own kind in its ``kind`` field, as a plugin's PluginMeta does.
        :param instances: The resources' Django ORM instances.
        :return: A broker, or a reference, for each resource, without duplicates. See :meth:`dependency_broker`.
        """
        unique = {instance.pk: instance for instance in instances}
        brokers: List[SAMDependency] = []
        for instance in unique.values():
            if kind:
                instance_kind = kind
            else:
                # a row that has its own kind, e.g. a PluginMeta, which models.Model doesn't declare
                row_kind = getattr(instance, "kind")
                instance_kind = getattr(row_kind, "value", row_kind)
            broker: SAMDependency
            if self._dependency_references_only:
                name = getattr(instance, "name")
                user_profile = getattr(instance, "user_profile")
                broker = SAMDependencyReference(kind=instance_kind, name=name, user_profile=user_profile)
            else:
                broker = self.dependency_broker(instance_kind, instance)
            brokers.append(broker)
        return brokers

    def dependency_references(self) -> List[SAMDependency]:
        """Return the kind, name and owner of each resource that depends on this resource, without building brokers.

        It is :meth:`dependencies`, with a :class:`SAMDependencyReference` in place of each broker, for
        the callers that need only those, such as ``describe``'s ``status.dependencies`` and the check
        before a delete. Building a broker per dependent costs its own lookups and logging, and a
        built-in resource can have many dependents. The dependencies are queried afresh, and the
        brokers that :meth:`dependencies` memoized, if any, are kept for it.

        :return: A reference for each resource that depends on this resource. A broker that builds
            its dependencies without :meth:`dependency_brokers` returns brokers here too.
        """
        memoized = self._dependencies
        self._dependencies = None
        self._dependency_references_only = True
        try:
            references = self.dependencies()
        finally:
            self._dependency_references_only = False
            self._dependencies = memoized
        return references

    def verify_no_dependencies(self, command: Optional[SmarterJournalCliCommands] = None) -> None:
        """Raise an error if other resources depend on this resource.

        Call this in :meth:`delete`, before deleting anything.

        :param command: The command that is being processed.
        :raises SAMBrokerErrorDependencies: If :meth:`dependency_references` returns any.
        """
        # the current dependencies, not those memoized by @memoized_dependencies.
        dependencies = self.dependency_references()
        if dependencies:
            visible = self.visible_dependencies(dependencies)
            names = sorted(f"{dependency.kind} {dependency.name}" for dependency in visible)
            hidden = len(dependencies) - len(visible)
            if hidden:
                names.append(
                    f"{hidden} {inflect_engine.plural('resource', hidden)} in other accounts"  # type: ignore[arg-type]
                )
            raise SAMBrokerErrorDependencies(
                f"Cannot delete {self.kind} {self.name}, because these resources depend on it: {', '.join(names)}. "
                "Delete them, or remove their references to it, first.",
                thing=self.kind,
                command=command,
            )

    def visible_dependencies(self, dependencies: Optional[List[SAMDependency]] = None) -> List[SAMDependency]:
        """Return the dependencies that the authenticated user may read.

        A dependency may belong to another account, e.g. an LLMClient that uses a built-in
        Guardrail. Superusers may read every dependency. Other users may read those of their
        own account.

        :param dependencies: The dependencies to filter. Defaults to :meth:`dependencies`.
        :return: The dependencies that the authenticated user may read.
        """
        if dependencies is None:
            dependencies = self.dependencies()
        if self.user is not None and getattr(self.user, "is_superuser", False):
            return dependencies
        visible = [dependency for dependency in dependencies if self.account and dependency.account == self.account]
        return visible

    def dependencies_status(self) -> List[SmarterDictType]:
        """Return the ``status.dependencies`` of a manifest: the kind and name of each visible dependency.

        Example:

        .. code-block:: python

            broker.dependencies_status()
            # [{"kind": "LLMClient", "name": "smarter_example"}]

        :return: A dict with the ``kind`` and ``name`` of each dependency that the authenticated user may read.
        """
        dependencies = self.dependency_references()
        visible = self.visible_dependencies(dependencies)
        visible_sorted = sorted(visible, key=lambda d: (str(d.kind), str(d.name)))
        status = [{"kind": dependency.kind, "name": dependency.name} for dependency in visible_sorted]
        return status

    @abstractmethod
    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Delete a resource.

        :param request: The HTTP request object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A SmarterJournaledJsonResponse containing the result of the delete operation.
        """
        raise SAMBrokerErrorNotImplemented(
            message="delete() not implemented", thing=self.thing, command=SmarterJournalCliCommands.DELETE
        )

    @abstractmethod
    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Deploy a resource.

        :param request: The HTTP request object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A SmarterJournaledJsonResponse containing the result of the deploy operation.
        """
        raise SAMBrokerErrorNotImplemented(
            message="deploy() not implemented", thing=self.thing, command=SmarterJournalCliCommands.DEPLOY
        )

    @abstractmethod
    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Returns an example yaml manifest document for the kind of resource.

        :param request: The HTTP request object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A SmarterJournaledJsonResponse containing the example manifest.
        """
        raise SAMBrokerErrorNotImplemented(
            message="example_manifest() not implemented",
            thing=self.thing,
            command=SmarterJournalCliCommands.MANIFEST_EXAMPLE,
        )

    @abstractmethod
    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Get information about specified resources.

        :param request: The HTTP request object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A SmarterJournaledJsonResponse containing the result of the get operation.
        """
        raise SAMBrokerErrorNotImplemented(
            message="get() not implemented", thing=self.thing, command=SmarterJournalCliCommands.GET
        )

    @abstractmethod
    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Get logs for a resource.

        :param request: The HTTP request object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A SmarterJournaledJsonResponse containing the logs for the resource.
        """
        raise SAMBrokerErrorNotImplemented(
            message="logs() not implemented", thing=self.thing, command=SmarterJournalCliCommands.LOGS
        )

    @abstractmethod
    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Undeploy a resource.

        :param request: The HTTP request object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A SmarterJournaledJsonResponse containing the result of the undeploy operation.
        """
        raise SAMBrokerErrorNotImplemented(
            message="undeploy() not implemented", thing=self.thing, command=SmarterJournalCliCommands.UNDEPLOY
        )

    def schema(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return the published JSON schema for the Pydantic model.

        :param request: The HTTP request object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: A SmarterJournaledJsonResponse containing the JSON schema.
        """
        command = SmarterJournalCliCommands(self.example_manifest.__name__)

        model = self.SAMModelClass
        data = model.model_json_schema()

        return self.json_response_ok(command=command, data=data)

    @classmethod
    def validation_errors(cls, manifest: SmarterDictType, external_checks: bool = True) -> list[SmarterDictType]:
        """Validate a manifest against the broker's Pydantic model, without saving it.

        Pydantic's errors keep their ``loc``, the path of the invalid value in the manifest.
        Errors that the model's validators raise as other exceptions, e.g. ``SAMValidationError``,
        have an empty ``loc``.

        By default the manifest is validated as one that a client sent, inside
        :func:`~smarter.lib.manifest.models.client_manifest_validation`, so validators that check
        something outside of the manifest also run, e.g. that an image url responds. A caller that
        must not make requests on a client's behalf, such as an anonymous endpoint, passes
        ``external_checks=False``.

        Example:

        .. code-block:: python

            SAMGuardrailBroker.validation_errors({"apiVersion": "smarter.sh/v1", "kind": "Guardrail"})
            # [{"loc": ["metadata"], "message": "Field required", "type": "missing"}, ...]

        :param manifest: The manifest, as a dict.
        :param external_checks: Whether to run the validators that check something outside of the manifest.
        :return: The manifest's errors, as dicts with a ``loc``, a ``message`` and a ``type``, or an empty list.
        """
        context = client_manifest_validation() if external_checks else contextlib.nullcontext()
        try:
            with context:
                cls._pydantic_model.model_validate(manifest)
        except ValidationError as e:
            errors = []
            for error in e.errors():
                loc = [str(part) for part in error["loc"]]
                errors.append({"loc": loc, "message": error["msg"], "type": error["type"]})
            return errors
        # pylint: disable=broad-except
        except Exception as e:
            message = getattr(e, "message", None)
            if not message:
                message = str(e)
            if not message:
                message = type(e).__name__
            return [{"loc": [], "message": message, "type": type(e).__name__}]
        return []

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
        Get or create a Smarter Secret in the database.

        This is used to store
        secrets that are passed in the manifest.

        :param user_profile: The UserProfile to associate the secret with.
        :param name: The name of the secret.
        :param value: The value of the secret.
        :param description: A description of the secret.
        :param expiration: The expiration date of the secret.
        :return: The created or retrieved Secret object.
        """

        secret: Optional[Secret] = None
        try:
            secret = Secret.objects.get(user_profile=user_profile, name=name)
        except Secret.DoesNotExist:
            pass

        if not secret:
            if not value:
                raise SAMBrokerError(
                    message=f"Secret {name} not found and no value was provided provided. Cannot create secret.",
                    thing=self.thing,
                    command=SmarterJournalCliCommands.GET,
                )

            if not user_profile:
                raise SAMBrokerError(
                    message=f"Secret {name} not found and no user_profile was provided provided. Cannot create secret.",
                    thing=self.thing,
                    command=SmarterJournalCliCommands.GET,
                )

            if not description:
                description = f"[auto generated] Secret {name} for {user_profile}"

            try:
                encrypted_value = Secret.encrypt(value)
                secret = Secret.objects.create(
                    user_profile=user_profile,
                    name=name,
                    description=description,
                    encrypted_value=encrypted_value,
                    expires_at=expiration,
                )
            except IntegrityError as ie:
                logger.error(
                    "%s.get_or_create_secret() IntegrityError creating Secret %s for user %s: %s",
                    self.abstract_broker_logger_prefix,
                    name,
                    user_profile,
                    ie,
                )
                raise SAMBrokerError(
                    message=f"Failed to create Secret {name} for user {user_profile}: {ie}",
                    thing=self.thing,
                ) from ie
            except Exception as create_exception:
                logger.error(
                    "%s.get_or_create_secret() Exception creating Secret %s for user %s: %s",
                    self.abstract_broker_logger_prefix,
                    name,
                    user_profile,
                    create_exception,
                )
                raise SAMBrokerError(
                    message=f"Failed to create Secret {name} for user {user_profile}: {create_exception}",
                    thing=self.thing,
                ) from create_exception

        if not secret:
            raise SAMBrokerError(
                message=f"Failed to create or retrieve {Secret.__name__} {name}",
                thing=self.thing,
            )
        return secret

    ###########################################################################
    # http json response helpers
    ###########################################################################
    def _retval(
        self,
        data: Optional[SmarterDictType] = None,
        error: Optional[SmarterDictType] = None,
        message: Optional[str] = None,
    ) -> SmarterDictType:
        retval: SmarterDictType = {}
        if data:
            retval[SmarterJournalApiResponseKeys.DATA] = data
        if error:
            retval[SmarterJournalApiResponseKeys.ERROR] = error
        if message:
            retval[SmarterJournalApiResponseKeys.MESSAGE] = message

        return retval

    def _request_or_raise(self, command: SmarterJournalCliCommands) -> HttpRequest:
        """
        Return the broker's request, which every journaled json response needs, or raise an error if it has none.

        :param command: The command that was executed.
        :returns: The request.
        :raises SAMBrokerError: If the broker has no request.
        """
        if self.request is None:
            raise SAMBrokerError(
                message="Cannot create JSON response without a valid request object",
                thing=self.thing,
                command=command,
            )
        return self.request

    def _error_without_exception(self, error_class: type, message: str) -> SmarterDictType:
        """
        Return the ``error`` of a response for an error that the broker reports without raising it.

        It has the same keys as the error of a response to a raised exception, without the stack trace,
        args, cause and context, which only an exception has.

        :param error_class: The class of the error, e.g. :class:`SAMBrokerErrorNotFound`.
        :param message: The error's description.
        :returns: The error.
        """
        error = {
            SmarterJournalApiResponseErrorKeys.ERROR_CLASS: error_class.__name__,
            SmarterJournalApiResponseErrorKeys.STACK_TRACE: None,
            SmarterJournalApiResponseErrorKeys.DESCRIPTION: message,
            SmarterJournalApiResponseErrorKeys.STATUS: "",
            SmarterJournalApiResponseErrorKeys.ARGS: None,
            SmarterJournalApiResponseErrorKeys.CAUSE: None,
            SmarterJournalApiResponseErrorKeys.CONTEXT: None,
        }
        return error

    def json_response_ok(
        self, command: SmarterJournalCliCommands, data: Optional[SmarterDictType] = None, message: Optional[str] = None
    ) -> SmarterJournaledJsonResponse:
        """Return a common success response.

        :param command: The command that was executed.
        :param data: The data to return in the response.
        :param message: An optional message to include in the response.
        :return: A SmarterJournaledJsonResponse containing the success response.
        :raises SAMBrokerError: If the broker has no request.
        """
        request = self._request_or_raise(command)
        data = data or {}

        operated = SmarterJournalCliCommands.past_tense().get(str(command), command)

        kind: Optional[str]
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
        if command == SmarterJournalCliCommands.DESCRIBE and isinstance(data.get(SAMKeys.STATUS.value), dict):
            try:
                data[SAMKeys.STATUS.value]["dependencies"] = self.dependencies_status()
            except (SAMBrokerError, SAMValidationError) as e:
                logger.warning(
                    "%s.json_response_ok() could not add the dependencies of %s %s to its status: %s",
                    self.abstract_broker_logger_prefix,
                    self.kind,
                    self.name,
                    e,
                )
        retval = self._retval(data=data, message=message)
        return SmarterJournaledJsonResponse(
            request=request, thing=self.thing, command=command, data=retval, status=HTTPStatus.OK, safe=False
        )

    def json_response_err_readonly(self, command: SmarterJournalCliCommands) -> SmarterJournaledJsonResponse:
        """Return a common read-only response.

        :param command: The command that was executed.
        :return: A SmarterJournaledJsonResponse containing the read-only response.
        :raises SAMBrokerError: If the broker has no request.
        """
        request = self._request_or_raise(command)
        message = f"{self.kind} {self.name} is read-only"

        error = self._error_without_exception(SAMBrokerReadOnlyError, message)
        retval = self._retval(error=error, message=message)
        return SmarterJournaledJsonResponse(
            request=request, thing=self.thing, command=command, data=retval, status=HTTPStatus.METHOD_NOT_ALLOWED
        )

    def json_response_err_notimplemented(self, command: SmarterJournalCliCommands) -> SmarterJournaledJsonResponse:
        """Return a common not implemented response.

        :param command: The command that was executed.
        :return: A SmarterJournaledJsonResponse containing the not implemented response.
        :raises SAMBrokerError: If the broker has no request.
        """
        request = self._request_or_raise(command)
        message = f"command not implemented for {self.kind} resources"
        error = self._error_without_exception(SAMBrokerErrorNotImplemented, message)
        retval = self._retval(error=error, message=message)
        return SmarterJournaledJsonResponse(
            request=request, thing=self.thing, command=command, data=retval, status=HTTPStatus.NOT_IMPLEMENTED
        )

    def json_response_err_notready(self, command: SmarterJournalCliCommands) -> SmarterJournaledJsonResponse:
        """Return a common not ready response.

        :param command: The command that was executed.
        :return: A SmarterJournaledJsonResponse containing the not ready response.
        :raises SAMBrokerError: If the broker has no request.
        """
        request = self._request_or_raise(command)
        message = f"{self.kind} {self.name} not ready"
        error = self._error_without_exception(SAMBrokerErrorNotReady, message)
        retval = self._retval(error=error, message=message)
        return SmarterJournaledJsonResponse(
            request=request, thing=self.thing, command=command, data=retval, status=HTTPStatus.BAD_REQUEST
        )

    def json_response_err_notfound(
        self, command: SmarterJournalCliCommands, message: Optional[str] = None
    ) -> SmarterJournaledJsonResponse:
        """Return a common not found response.

        :param command: The command that was executed.
        :param message: An optional custom message to include in the response.
        :return: A SmarterJournaledJsonResponse containing the not found response.
        :raises SAMBrokerError: If the broker has no request.
        """
        request = self._request_or_raise(command)
        message = message or f"{self.kind} {self.name} not found"
        error = self._error_without_exception(SAMBrokerErrorNotFound, message)
        retval = self._retval(error=error, message=message)
        return SmarterJournaledJsonResponse(
            request=request, thing=self.thing, command=command, data=retval, status=HTTPStatus.NOT_FOUND
        )

    def json_response_err(self, command: SmarterJournalCliCommands, e: Exception) -> SmarterJournaledJsonResponse:
        """
        Return a structured error response that can be unpacked and rendered by the cli in a variety of formats.

        :param command: The command that was executed.
        :param e: The exception that was raised.
        :return: A SmarterJournaledJsonResponse containing the error response.
        :raises SAMBrokerError: If the broker has no request.
        """
        request = self._request_or_raise(command)
        stack_trace = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        return SmarterJournaledJsonErrorResponse(
            request=request,
            thing=self.thing,
            command=command,
            e=e,
            stack_trace=stack_trace,
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    ###########################################################################
    # data transformation helpers
    ###########################################################################
    def set_and_verify_name_param(self, *args, command: Optional[SmarterJournalCliCommands] = None, **kwargs) -> None:
        """
        Set the broker's name from the ``name`` keyword argument, if it has one.

        Nothing is verified, and nothing is raised: without a ``name``, the broker keeps its name.

        :param args: Not used.
        :param command: The command being executed. Not used.
        :param kwargs: The command's keyword arguments, which may have a ``name``.
        """
        name = kwargs.get("name")
        if name:
            self.name_cached_property_setter(name)

    # pylint: disable=W0212
    def get_model_titles(self, serializer: ModelSerializer) -> Optional[list[dict[str, str]]]:
        """
        For tabular output from get() implementations.

        Returns a list of field names and types
        from the Django model serializer.

        :param serializer: The Django model serializer instance.
        :return: A list of field names and types.
        """
        fields_and_types: list[dict[str, str]] = []
        for field_name, field in serializer.fields.items():
            # the field name is camelCased to match the keys of the camelCased items that get() returns
            item = {"name": self.to_camel_case(field_name), "type": type(field).__name__}
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

    def filter_by_annotation_selector(self, queryset: QuerySetType, kwargs: SmarterDictType) -> QuerySetType:
        """
        Filter a ``get`` command's resources by the annotation selector in its query parameters.

        The selector is the ``annotation`` query parameter, which may be repeated, e.g.
        ``?annotation=acme.com/crm-account-id=A-10042&annotation=!acme.com/archived``. Every
        requirement must match. See :mod:`smarter.lib.annotation.selectors`.

        :param queryset: The resources that the requester may read.
        :param kwargs: The ``get`` command's keyword arguments, which hold the query parameters.
        :raises smarter.lib.annotation.validation.SmarterAnnotationError: If the selector is invalid, which is a 400.
        :returns: The resources that match the selector.
        """
        return filter_by_annotations(queryset, kwargs.get(ANNOTATION_SELECTOR_PARAM))

    def clean_cli_param(self, param: Any, param_name: str = "unknown", url: Optional[str] = None) -> Optional[str]:
        """
        Clean a cli parameter: strip a string's whitespace, and turn an empty string into None.

        A parameter that is not a string is logged as a warning. A list becomes its first element,
        and any other value is returned unchanged.

        :param param: The param to clean.
        :param param_name: The name of the param, for logging purposes.
        :param url: The url from which the param was extracted, for logging purposes.
        :return: The cleaned param.
        """
        if isinstance(param, str):
            retval: Optional[str] = param.strip()
            if not retval:
                logger.warning(
                    "%s.clean_cli_param() param <%s> is an empty string, setting to None for url: %s",
                    self.formatted_class_name,
                    param_name,
                    url,
                )
                retval = None
            return retval

        logger.warning(
            "%s.clean_cli_param() param: <%s>. Expected str but got type: %s (%s) for url: %s",
            self.formatted_class_name,
            param_name,
            type(param),
            param,
            url,
        )
        if isinstance(param, list):
            first_element = param[0]
            logger.warning(
                "%s.clean_cli_param() set param <%s> to first element of list: %s for url: %s",
                self.formatted_class_name,
                param_name,
                param,
                url,
            )
            return first_element
        return param

    def readable_by_name(
        self,
        model_class: Type[MetaDataWithOwnershipModel],
        owned: Optional[MetaDataWithOwnershipModel],
        name: Optional[str] = None,
    ) -> Optional[MetaDataWithOwnershipModel]:
        """
        Return the resource to describe: the user's own, or else one with this name that the user may read.

        ``get`` lists every resource that the user may read, including the ones that are shared
        with the account, e.g. built-in Guardrails. ``describe`` must find each of them by the
        name that ``get`` returned. ``apply`` and ``delete`` must not: they act on the user's own
        resource only.

        :param model_class: The resource's Django model.
        :param owned: The user's own resource of this name, if any.
        :param name: The resource's name. Defaults to the broker's name.
        :returns: The resource, or None if the user may read none of this name.
        """
        if owned is not None:
            return owned
        name = name or self.name
        if not name or not self.user_profile:
            return None
        readable = model_class.objects.with_read_permission_for(self.user_profile.user)  # type: ignore[attr-defined]
        resource = readable.filter(name=name).order_by("pk").first()
        return resource

    def command_result(self) -> SmarterDictType:
        """
        The ``data`` of the response to a command that changed the resource, e.g. apply.

        It identifies the resource, and nothing else. Use :meth:`to_json` for logging only: it
        includes the broker's request, authentication and cache key, which a client must not see.

        :returns: The resource's api version, kind and name.
        :raises SAMBrokerInternalError: If the broker has no kind.
        """
        if not self.kind:
            raise SAMBrokerInternalError(f"{self.__class__.__name__} {self.name} has no kind")
        return SAMBrokerCommandResult(apiVersion=self.api_version, kind=self.kind, name=self.name).dump()

    def to_json(self) -> SmarterDictType:
        """
        Serialize the broker instance to a dict, with its keys sorted, for logging.

        It includes the broker's internal state, e.g. its request, authentication and cache key,
        so it is never returned to a client. See :meth:`command_result`.

        :return: A JSON-serializable dict representation of the broker instance.
        """
        orm_instance_obj = None
        if self.orm_instance:
            serialized = serializers.serialize("json", [self.orm_instance])
            try:
                if serialized:
                    orm_instance_obj = json.loads(serialized)[0]
            # pylint: disable=W0703
            except Exception:
                logger.warning(
                    "%s.to_json() - failed to serialize orm_instance: %s",
                    self.abstract_broker_logger_prefix,
                    serialized,
                )

        api_version = self.api_version
        kind = self.kind
        name = self.name
        manifest = self.manifest
        if isinstance(manifest, AbstractSAMBase):
            manifest = manifest.model_dump()
        loader_json = None
        if self.loader:
            loader_json = self.loader.to_json()
        orm_model_class_name = None
        if self.ORMModelClass:
            orm_model_class_name = self.ORMModelClass.__name__
        serializer_class_name = None
        if self.SerializerClass:
            serializer_class_name = self.SerializerClass.__name__

        state = {
            "api_version": api_version,
            "kind": kind,
            "name": name,
            "manifest": manifest,
            "loader": loader_json,
            "orm_model_class": orm_model_class_name,
            "serializer_class": serializer_class_name,
            "orm_instance": orm_instance_obj,
            **super().to_json(),
        }
        return self.sorted_dict(state)

    def log_abstract_broker_state(self) -> None:
        """
        Log the current state of the AbstractBroker instance for debugging purposes.

        A ready broker's state is logged at DEBUG, which is usually switched off, so it is built
        only when it will be logged: it reads the broker's ready state and ORM instance, which
        would otherwise cost every broker queries that its caller may never need. A broker that
        is not ready is logged at DEBUG too: a command that needs no single resource, e.g. ``get``,
        never makes it ready, and one that does fails with :class:`SAMBrokerErrorNotReady`, which
        the cli view logs.
        """
        if not logger.should_log(logging.DEBUG):
            return
        state = {
            "ready": self.ready,
            "name": self.known_name,
            "manifest": bool(self._manifest),
            "loader": bool(self._loader),
            "orm_instance": bool(self.orm_instance),
            "request": self.url,
            "user_profile": self.user_profile,
        }
        logger.debug(
            "%s.log_abstract_broker_state() %s broker is %s: %s",
            self.abstract_broker_logger_prefix,
            self.kind,
            self.abstract_broker_ready_state,
            logging.SmarterFormattedText.json(state),
        )


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
    def ORMModelClass(self) -> Type[MetaDataWithOwnershipModel]:
        """
        Not implemented.

        :raises SAMBrokerErrorNotImplemented: Always.
        """
        raise SAMBrokerErrorNotImplemented(
            message="Subclasses must implement the ORMModelClass", thing=self.thing, command=None
        )

    @property
    def SerializerClass(self) -> Type[ModelSerializer]:
        """
        Not implemented.

        :raises SAMBrokerErrorNotImplemented: Always.
        """
        raise SAMBrokerErrorNotImplemented(
            message="Subclasses must implement the SerializerClass", thing=self.thing, command=None
        )

    @property
    def manifest(self) -> Optional[Union[AbstractSAMBase, SmarterDictType]]:
        """
        Not implemented.

        :raises SAMBrokerErrorNotImplemented: Always.
        """
        raise SAMBrokerErrorNotImplemented("Subclasses must implement the manifest property.")

    def prompt(self, request: SmarterRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Delegate to :meth:`AbstractBroker.prompt`.

        :param request: The request.
        :param args: Passed through.
        :param kwargs: Passed through.
        """
        return super().prompt(request, *args, **kwargs)

    def dependencies(self) -> List[SAMDependency]:
        """Delegate to :meth:`AbstractBroker.dependencies`."""
        return super().dependencies()

    def delete(self, request: SmarterRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Delegate to :meth:`AbstractBroker.delete`.

        :param request: The request.
        :param args: Passed through.
        :param kwargs: Passed through.
        """
        return super().delete(request, *args, **kwargs)

    def deploy(self, request: SmarterRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Delegate to :meth:`AbstractBroker.deploy`.

        :param request: The request.
        :param args: Passed through.
        :param kwargs: Passed through.
        """
        return super().deploy(request, *args, **kwargs)

    def describe(self, request: SmarterRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Delegate to :meth:`AbstractBroker.describe`.

        :param request: The request.
        :param args: Passed through.
        :param kwargs: Passed through.
        """
        return super().describe(request, *args, **kwargs)

    def example_manifest(self, request: SmarterRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Delegate to :meth:`AbstractBroker.example_manifest`.

        :param request: The request.
        :param args: Passed through.
        :param kwargs: Passed through.
        """
        return super().example_manifest(request, *args, **kwargs)

    def get(self, request: SmarterRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Delegate to :meth:`AbstractBroker.get`.

        :param request: The request.
        :param args: Passed through.
        :param kwargs: Passed through.
        """
        return super().get(request, *args, **kwargs)

    def logs(self, request: SmarterRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Delegate to :meth:`AbstractBroker.logs`.

        :param request: The request.
        :param args: Passed through.
        :param kwargs: Passed through.
        """
        return super().logs(request, *args, **kwargs)

    def undeploy(self, request: SmarterRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Delegate to :meth:`AbstractBroker.undeploy`.

        :param request: The request.
        :param args: Passed through.
        :param kwargs: Passed through.
        """
        return super().undeploy(request, *args, **kwargs)
