"""Pydantic models for Smarter API Manifests."""

import abc
import datetime
import re
from contextlib import contextmanager
from contextvars import ContextVar
from logging import getLogger
from typing import Iterator, List, Optional

from django.utils.text import slugify
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    field_validator,
    model_validator,
)

from smarter.apps.account.models import (
    User,
    UserProfile,
    get_resolved_user,
    is_authenticated_user,
)
from smarter.common.api import SmarterApiVersions
from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.common.mixins import SmarterHelperMixin
from smarter.common.utils import to_snake_case
from smarter.lib.annotation.validation import (
    SmarterAnnotationError,
    normalize_annotations,
)
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.exceptions import SAMValidationError

logger = getLogger(__name__)
logger_prefix = SmarterFormattedText.text(__name__)

_CLIENT_MANIFEST: ContextVar[bool] = ContextVar("smarter_client_manifest", default=False)


@contextmanager
def client_manifest_validation() -> Iterator[None]:
    """
    Validate, inside this context, a manifest that a client sent, e.g. to apply or validate it.

    Brokers validate a client's manifest inside it. Models that they build from the database are
    validated outside of it. Validators that check something outside of the manifest, such as that a
    url is available, run only inside it (see :func:`is_client_manifest`), so that describing a
    resource never depends on the network.

    A context variable is used rather than Pydantic's validation context, because
    :class:`SmarterBasePydanticModel` overrides ``__init__``, through which Pydantic validates nested
    models without the validation context.

    Example:

    .. code-block:: python

        with client_manifest_validation():
            spec = SAMLLMClientSpec(**manifest["spec"])
    """
    token = _CLIENT_MANIFEST.set(True)
    try:
        yield
    finally:
        _CLIENT_MANIFEST.reset(token)


def is_client_manifest() -> bool:
    """
    Whether the manifest that is being validated is one that a client sent.

    :returns: True inside :func:`client_manifest_validation`.
    :rtype: bool
    """
    return _CLIENT_MANIFEST.get()


class SmarterBasePydanticModel(BaseModel, SmarterHelperMixin):
    """Smarter API Base Pydantic Model."""

    _user: Optional[User] = PrivateAttr(default=None)
    _user_profile: Optional[UserProfile] = PrivateAttr(default=None)

    model_config = ConfigDict(
        from_attributes=True,  # allow model to be initialized from class attributes
        arbitrary_types_allowed=True,  # allow Field attributed to be created from custom class types
        frozen=True,  # models are read-only
    )

    def __init__(self, **data):
        """Add support for passing a 'user' argument when initializing the model, which will be stored in a private attribute."""
        user_profile = data.pop("user_profile", None)
        user = data.pop("user", None)
        super().__init__(**data)
        if isinstance(user_profile, UserProfile):
            self._user_profile = user_profile
            self._user = user_profile.user
        elif user is not None:
            user = get_resolved_user(user)
            if is_authenticated_user(user):  # type: ignore
                self._user_profile = UserProfile.get_cached_object(user=user)  # type: ignore
                if isinstance(self._user_profile, UserProfile):
                    self._user = self._user_profile.user

    @model_validator(mode="before")
    def coerce_none_strings(cls, data):
        if isinstance(data, dict):
            for k, v in data.items():
                if v in ("None", ""):
                    data[k] = None
        return data

    @property
    def user(self) -> Optional[User]:
        """Get the user associated with this manifest, if any."""
        return self._user

    @property
    def user_profile(self) -> Optional[UserProfile]:
        """Get the user profile associated with this manifest, if any."""
        return self._user_profile


class AbstractSAMMetadataBase(SmarterBasePydanticModel, abc.ABC):
    """
    Abstract base class for manifest metadata in the Smarter API.

    This class defines the required structure and validation logic for metadata associated with
    Smarter API manifests. It is designed to be subclassed by concrete manifest metadata classes,
    which may extend or customize the metadata fields as needed for specific resource types.

    The ``AbstractSAMMetadataBase`` enforces strong typing and validation for core metadata fields,
    such as resource name, description, version, tags, and annotations. It ensures that all metadata
    adheres to expected formats and constraints, promoting consistency and reliability across all
    manifest definitions.

    Subclasses should inherit from this class to implement metadata for their specific manifest
    types. This approach encourages code reuse, enforces validation, and provides a unified
    interface for working with manifest metadata throughout the Smarter API ecosystem.

    .. note::

        This class is abstract and should not be instantiated directly. Instead, create subclasses
        that define any additional fields or validation required for your manifest's metadata.
    """

    name: str = Field(..., description="The camelCase name of the manifest resource")
    description: Optional[str] = Field(
        ..., description="The description for this resource. Be brief. Keep it under 255 characters."
    )
    version: Optional[str] = Field(..., description="The semantic version of the manifest. Example: 0.1.0")
    tags: Optional[List[str]] = Field(
        default_factory=list,
        description="The tags of the manifest. Used for generic resource categorization and search. Example: ['tag1', 'tag2']",
    )
    annotations: Optional[dict[str, str]] = Field(
        default_factory=dict,
        description=(
            "Annotations, as in Kubernetes: a map of keys to string values that clients and integrations "
            "attach to a resource for their own purposes, e.g. to associate it with a resource in another "
            "system. A key is an optional DNS-subdomain prefix that names its owner, then a slash and a "
            "name of one or more slash-separated segments, e.g. 'acme.com/crm-account-id'. The prefix "
            "'smarter.sh' and its subdomains are reserved for the Smarter platform. Values are strings: "
            "unquoted YAML scalars such as true, 42 or dates are converted to strings, and structured data "
            "belongs in a JSON string. All annotations together are limited to 256 KiB. The list of "
            "one-key maps of older manifests, e.g. [{'acme.com/crm-account-id': 'A-10042'}], is also accepted."
        ),
        examples=[{"acme.com/crm-account-id": "A-10042", "smarter.sh/llmclient/use-case": "customer support"}],
    )

    @field_validator("name")
    def validate_name(cls, v) -> str:
        """
        Validates the ``name`` field for a manifest.

        Ensures the value is a string, present, and meets all constraints. Raises if not a string.
        """
        if not isinstance(v, str):
            raise SAMValidationError(f"Manifest 'name' must be a string, got {type(v)}.")
        v = v.strip()
        if v == "":
            raise SAMValidationError("Missing required key name")
        if len(v) > 50:
            raise SAMValidationError("Name must be less than 50 characters")
        if not re.match(SmarterValidator.VALID_CLEAN_STRING_WITH_SPACES, v):
            raise SAMValidationError(
                f"Invalid name: {v}. Ensure that you do not include characters that are not URL friendly."
            )
        slugified = str(slugify(v, allow_unicode=False)).replace("-", "_")
        if slugified != v:
            logger.warning(
                "%s.name '%s' is not URL-friendly. Converting to URL-friendly format: %s. Please use URL-friendly characters for names.",
                logger_prefix + f".{cls.__name__}",
                v,
                slugified,
            )
            v = slugified
        if not SmarterValidator.is_valid_snake_case(v):
            snake_case_name = to_snake_case(v)
            logger.warning(
                "%s.name '%s' is not in snake_case. Converting to snake_case: %s. Please use snake_case for names.",
                logger_prefix + f".{cls.__name__}",
                v,
                snake_case_name,
            )
            v = snake_case_name
        # Final guarantee: always return a string
        if not isinstance(v, str):
            raise SAMValidationError(f"Manifest 'name' must be a string after processing, got {type(v)}.")
        return v

    @field_validator("description")
    def validate_description(cls, v) -> Optional[str]:
        """
        Validates the ``description`` field for a manifest.

        This method ensures that the ``description`` attribute is present. If the value is missing,
        a ``SAMValidationError`` is raised.

        :param v: The value of the ``description`` field to validate.
        :type v: str
        :raises smarter.lib.manifest.exceptions.SAMValidationError: If the value is missing.
        :return: The validated ``description`` string.
        :rtype: str
        """
        return v.strip() if isinstance(v, str) and v.strip() != "" else None

    @field_validator("version")
    def validate_version(cls, v) -> Optional[str]:
        """
        Validates the ``version`` field for a manifest.

        This method ensures that the ``version`` attribute is present and follows semantic versioning
        rules. If the value is missing or invalid, a ``SAMValidationError`` is raised

        :param v: The value of the ``version`` field to validate.
        :type v: str
        :raises smarter.lib.manifest.exceptions.SAMValidationError: If the value is missing or invalid.
        :return: The validated ``version`` string.
        :rtype: str
        """
        if v in [None, ""]:
            return None
        if not re.match(SmarterValidator.VALID_SEMANTIC_VERSION, v):
            raise SAMValidationError(
                f"Invalid semantic version. Expected semantic version (ie '1.0.0-alpha') but got {v}"
            )
        return v

    @field_validator("tags")
    def validate_tags(cls, v) -> Optional[List[str]]:
        """
        Validates the ``tags`` field for a manifest.

        This method ensures that each tag in the ``tags`` list adheres to URL-friendly character
        rules. If any tag is invalid, a ``SAMValidationError`` is raised.

        :param v: The value of the ``tags`` field to validate.
        :type v: Optional[List[str]]
        :raises smarter.lib.manifest.exceptions.SAMValidationError: If any tag is invalid.
        :return: The validated list of tags.
        :rtype: Optional[List[str]]
        """
        if v is None:
            return v
        if isinstance(v, list):
            v = [str(tag).strip() for tag in v]
            for tag in v:
                if not re.match(SmarterValidator.VALID_CLEAN_STRING_WITH_SPACES, tag):
                    raise SAMValidationError(
                        f"Invalid tag: {tag}. Ensure that you do not include characters that are not URL friendly."
                    )
        return v

    @field_validator("annotations", mode="before")
    def normalize_annotations(cls, v) -> Optional[dict[str, str]]:
        """
        Validate the ``annotations`` field, and return it as a map of strings to strings.

        Accepts a map, the list of one-key maps of older manifests, or either as a JSON string. See
        :func:`smarter.lib.annotation.validation.normalize_annotations`.

        :param v: The value of the ``annotations`` field.
        :type v: AnnotationsInput
        :raises smarter.lib.manifest.exceptions.SAMValidationError: If a key or value is invalid.
        :return: The annotations.
        :rtype: Optional[dict[str, str]]
        """
        if v is None:
            return v
        try:
            return normalize_annotations(v)
        except SmarterAnnotationError as e:
            raise SAMValidationError(str(e)) from e


class AbstractSAMSpecBase(SmarterBasePydanticModel, abc.ABC):
    """Pydantic Spec base class.

    Expected to be subclassed by specific manifest classes.
    """


class SAMDependency(SmarterBasePydanticModel):
    """A resource that depends on the resource that a manifest describes."""

    kind: str = Field(
        ...,
        description="kind[String]: The SAM kind of the resource that depends on this resource, e.g. LLMClient. Read only.",
    )

    name: str = Field(
        ...,
        description="name[String]: The name of the resource that depends on this resource. Read only.",
    )


class SAMDependencyTreeNode(SmarterBasePydanticModel):
    """
    A resource in a dependency tree: the resource, and, recursively, every resource that it uses.

    It is the opposite direction of :class:`SAMDependency`, which lists the resources that depend
    on a resource. An LLMClient's tree has its Provider, its plugins, their Connections, and those
    Connections' Secrets. See :meth:`smarter.lib.manifest.broker.AbstractBroker.dependency_tree`.

    A resource that the user may not read keeps its kind and record locator, so that the tree still
    shows that something is there, but not its name, owner or urls, or what it uses in turn.

    Each readable resource has two urls: ``url``, its manifest page in the web console, where its
    manifest can be edited, and ``detailUrl``, the api of its detail (its manifest, what it uses and
    what uses it), which a resource's detail dialog in the web console shows when its card is chosen.

    Example:

    .. code-block:: json

        {
          "kind": "LLMClient",
          "icon": "artificial-intelligence",
          "name": "stackademy_sql",
          "owner": "Ada Lovelace (ada)",
          "recordLocator": "llmclient-rMTAwMDAxMwx",
          "url": "/workbench/llm-clients/rMTAwMDAxMwx/manifest/",
          "detailUrl": "/dashboard/api/resource/LLMClient/llmclient-rMTAwMDAxMwx/",
          "readable": true,
          "children": [
            {
              "kind": "SqlPlugin",
              "icon": "file-sheet",
              "name": "stackademy_sql",
              "owner": "Ada Lovelace (ada)",
              "recordLocator": "pluginmeta-rMTEx",
              "url": "/llm-tools/plugins/rMTEx/",
              "detailUrl": "/dashboard/api/resource/SqlPlugin/pluginmeta-rMTEx/",
              "readable": true,
              "children": []
            }
          ]
        }
    """

    # a node always has every field, so its JSON Schema, from which the workbench's Architecture tab
    # generates its TypeScript types, marks the fields that have defaults as required too.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    kind: str = Field(
        ...,
        description="kind[String]: The SAM kind of the resource, e.g. LLMClient. Read only.",
    )

    icon: str = Field(
        ...,
        description=(
            "icon[String]: The kind's icon in the web console, a Keen Icons name without its ki- prefix, e.g. "
            "lock-2 for a Secret. See sam_kind_icon(). Read only."
        ),
    )

    name: Optional[str] = Field(
        default=None,
        description=(
            "name[String]: The name of the resource, or an Extension's slug, e.g. weather. None if the user may not "
            "read it. Read only."
        ),
    )

    owner: Optional[str] = Field(
        default=None,
        description=(
            "owner[String]: Who owns the resource: its owner's full name and username, e.g. Ada Lovelace (ada), "
            "or an Extension's publisher. None if the user may not read it, or if it has no owner. Read only."
        ),
    )

    recordLocator: Optional[str] = Field(
        default=None,
        description=(
            "recordLocator[String]: The resource's record locator, e.g. llmclient-rMTAwMDAxMwx, from which its "
            "web console url is derived. None for a resource that has none, e.g. a User. Read only."
        ),
    )

    url: Optional[str] = Field(
        default=None,
        description=(
            "url[String]: The path of the resource's manifest page in the web console, where its manifest can be "
            "edited, derived from its record locator. None if it has no page, or if the user may not read it. "
            "Read only."
        ),
    )

    detailUrl: Optional[str] = Field(
        default=None,
        description=(
            "detailUrl[String]: The path of the api of the resource's detail in the web console: its manifest, "
            "the resources that it uses and those that use it. See "
            "smarter.apps.dashboard.resource_detail.resource_detail_url(). None if the user may not read it, "
            "or on a public page. Read only."
        ),
    )

    readable: bool = Field(
        default=True,
        description="readable[Boolean]: Whether the user may read the resource. Read only.",
    )

    children: List["SAMDependencyTreeNode"] = Field(
        default_factory=list,
        description="children[List]: The resources that this resource uses, each with its own tree. Read only.",
    )


class AbstractSAMStatusBase(SmarterBasePydanticModel, abc.ABC):
    """Pydantic Status base class.

    Expected to be subclassed by specific manifest classes.
    """

    recordLocator: str = Field(
        ...,
        description="recordLocator[String]: An optional identifier used to locate the resource record associated with this manifest. Read only.",
    )

    created: datetime.datetime = Field(
        ...,
        description="The date in which this resource was created. Read only.",
    )

    modified: datetime.datetime = Field(
        ...,
        description="The date in which this resource was most recently changed. Read only.",
    )

    dependencies: Optional[List[SAMDependency]] = Field(
        default=None,
        description=(
            "dependencies[List]: The resources that depend on this resource, and that must be deleted, or stop "
            "referring to it, before it can be deleted. Lists only the resources that you can read. Read only."
        ),
    )


class AbstractSAMBase(SmarterBasePydanticModel, abc.ABC):
    """
    Abstract base class for all Smarter API Manifest (SAM) models.

    This class serves as the foundational Pydantic model for representing Smarter API manifests.
    It is intended to be subclassed by concrete manifest classes that define specific resource types
    within the Smarter API ecosystem.

    The ``AbstractSAMBase`` class provides a strongly-typed structure for manifest data, ensuring
    that all manifests adhere to a consistent schema and validation logic. It includes built-in
    validation for core manifest fields and supports structured access to manifest data.

    Subclasses should implement or extend this class to define the specific data and behaviors
    required for their respective manifest types. This design promotes code reuse, type safety,
    and robust validation across all Smarter API manifests.

    The class also provides methods for validating manifest data and for representing the manifest
    as a string for debugging or logging purposes.

    .. note::

        Do not instantiate this class directly. Instead, create subclasses that define the
        required fields and any additional validation or methods specific to your manifest type.
    """

    apiVersion: str = Field(
        ...,
        description="apiVersion[String]: Required. The API version of the AbstractSAMBase.",
    )
    kind: str = Field(
        ...,
        description="kind[String]: Required. The kind of resource described by the manifest.",
    )
    metadata: AbstractSAMMetadataBase = Field(..., description="metadata[obj]: Required. The manifest metadata.")
    spec: AbstractSAMSpecBase = Field(..., description="spec[obj]: Required. The manifest specification.")
    status: Optional[AbstractSAMStatusBase] = Field(
        default=None,
        description="status[obj]: Optional. Read-only. The run-time state of the resource described by the manifest.",
    )

    @field_validator("apiVersion")
    def validate_apiVersion(cls, v) -> str:
        """
        Validates the ``apiVersion`` field for a manifest.

        This method ensures that the ``apiVersion`` attribute is present and matches one of the
        supported API versions defined in ``SmarterApiVersions``. If the value is missing or invalid,
        a ``SAMValidationError`` is raised.

        :param v: The value of the ``apiVersion`` field to validate.
        :type v: str
        :raises smarter.lib.manifest.exceptions.SAMValidationError: If the value is missing or not a supported version.
        :return: The validated ``apiVersion`` string.
        :rtype: str
        """
        if v in [None, ""]:
            raise SAMValidationError("Missing required manifest key: apiVersion")
        if v not in SmarterApiVersions.all():
            raise SAMValidationError(f"Invalid version. Must be one of {SmarterApiVersions.all()} but got {v}")
        return v

    @field_validator("metadata")
    def validate_metadata(cls, v) -> AbstractSAMMetadataBase:
        """
        Validates the ``metadata`` field for a manifest.

        This method ensures that the ``metadata`` attribute is an instance of
        :class:`AbstractSAMMetadataBase`. If a dictionary is provided, it will be coerced
        into an ``AbstractSAMMetadataBase`` object. This guarantees that the manifest metadata
        is always properly structured and validated.

        :param v: The value of the ``metadata`` field to validate.
        :type v: dict or AbstractSAMMetadataBase
        :return: The validated ``metadata`` object.
        :rtype: AbstractSAMMetadataBase
        """
        if isinstance(v, dict):
            return AbstractSAMMetadataBase(**v)
        return v

    def __str__(self) -> str:
        return f"{self.formatted_class_name}(apiVersion={self.apiVersion}, kind={self.kind})"
