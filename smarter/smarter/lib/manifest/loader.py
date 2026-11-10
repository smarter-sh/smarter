"""Smarter API Manifest Loader base class."""

import copy
from enum import Enum
from typing import Any, Optional, Union

import requests
import yaml

from smarter.common.api import SmarterApiVersions
from smarter.common.mixins import SmarterHelperMixin
from smarter.lib import json, logging
from smarter.lib.typing import SmarterDictType

from .enum import SAMDataFormats, SAMKeys, SAMMetadataKeys, SAMSpecificationKeyOptions
from .exceptions import SAMExceptionBase

logger = logging.getLogger(__name__)

SUPPORTED_API_VERSIONS = [SmarterApiVersions.V1]


class SAMLoaderError(SAMExceptionBase):
    """
    The error that :class:`SAMLoader` and :func:`validate_key` raise.

    It is raised for a manifest that cannot be loaded or validated: an unsupported api version,
    no manifest source or more than one, a format that is neither JSON nor YAML, or a missing
    top-level key.

    :param message: What went wrong, e.g. ``Missing required key: apiVersion``.

    .. code-block:: python

        try:
            loader = SAMLoader(manifest=my_manifest)
        except SAMLoaderError as err:
            print(f"Manifest validation failed: {err}")

    .. note::

        The :attr:`get_formatted_err_message` property is a fixed label,
        ``Smarter API Manifest Loader Error``, for logging and display.
    """

    @property
    def get_formatted_err_message(self) -> str:
        """Return the static formatted error message for SAMLoader errors."""
        return "Smarter API Manifest Loader Error"


def validate_key(key: str, key_value: Any, spec: Any) -> None:
    """
    Validate a manifest key and its value against a specification.

    This function enforces schema rules for manifest keys and values, supporting multiple validation strategies
    based on the type of the specification provided. It is a foundational utility for manifest validation
    and is used throughout the Smarter API Manifest Loader system.

    **Parameters**

    :param key: The manifest key to validate. Must be a string or an Enum with a string value.

    :param key_value: The value associated with the manifest key. The expected type and constraints depend on the specification.

    :param spec: The specification against which the key and value are validated. This can be:
        - A list: The value must be one of the items in the list.
        - A tuple: The first element is the expected data type; the second is a list of key options (e.g., required, optional, readonly).
        - Any other type: The value must match the type and value of the spec.

    **Validation Logic**

    - If the specification is a list, the value must be present in the list.
    - If the specification is a tuple, the value's type and presence are validated according to the tuple's contents:
        - The first element is the expected type (e.g., `str`, `dict`).
        - The second element is a list of options, such as `REQUIRED`, `OPTIONAL`, or `READONLY`.
        - If the key is required and the value is missing or empty, an error is raised.
        - If the value's type does not match the expected type, an error is raised.
    - If the specification is any other type, the value must match both the type and the value of the spec.

    **Examples**

    .. code-block:: python

        # Example 1: List validation
        validate_key("color", "red", ["red", "green", "blue"])
        # Passes if "red" is in the list

        # Example 2: Tuple validation
        validate_key("name", "Widget", (str, [SAMSpecificationKeyOptions.REQUIRED]))
        # Passes if "Widget" is a string and the key is required

        # Example 3: Exact value validation
        validate_key("apiVersion", "v1", "v1")
        # Passes if the value matches the spec exactly

    .. note::

        - All manifest keys must be strings. If an Enum is provided, its value is used.
        - If the value is missing or of the wrong type, a `SAMLoaderError` is raised with a descriptive message.
        - This function is intended for internal use in manifest validation routines and is not typically called directly.

    .. attention::

        - Ensure that the specification accurately reflects the schema requirements for your manifest type.
        - Improper use of this function may result in manifest validation failures or runtime errors.

    :raises SAMLoaderError: If the key or value does not conform to the specification.
    """
    # all keys must be strings
    if isinstance(key, Enum):
        key = key.value
    if not isinstance(key, str):
        raise SAMLoaderError(f"Invalid data type for key {key}. Expected str but got {type(key)}")

    # validate that key's value exists in the spec list
    if isinstance(spec, list):
        if key_value not in spec:
            raise SAMLoaderError(f"Invalid value {key_value} for key {key}. Expected one of {spec}")

    # validate that key value's data type matches the spec's data type, and if required, that the key exists
    elif isinstance(spec, tuple):
        type_spec = spec[0]
        options_list = spec[1]
        # validate that value exists for required key
        if SAMSpecificationKeyOptions.REQUIRED in options_list and not key_value:
            raise SAMLoaderError(f"Missing required key {key}")
        if SAMSpecificationKeyOptions.OPTIONAL not in options_list and not isinstance(key_value, type_spec):
            raise SAMLoaderError(
                f"Invalid data type for key {key}. Expected {spec[0]} but got {type(key_value)}: key_value={key_value} spec={spec[0]}"
            )

    # validate that key value is the same as the spec value
    else:
        if not isinstance(key_value, type(spec)):
            # possibility #1: the data is missing, so it's a NoneType
            if key_value is None:
                raise SAMLoaderError(f"Missing required key {key}")
            # possibility #2: the data exists but is the wrong type
            raise SAMLoaderError(
                f"Invalid key_value type for key {key}. Expected {type(spec)} but got {type(key_value)}"
            )
        if key_value != spec:
            raise SAMLoaderError(f"Invalid value for key {key}. Expected {spec} but got {key_value}")


class SAMLoader(SmarterHelperMixin):
    """
    Smarter API Manifest Loader base class.

    This class provides the foundational logic for loading, parsing, and validating
    Smarter API Manifest files, prior to attempting to use the manifest data for
    initializing a Pydantic model. It is designed to handle manifests provided as JSON or YAML,
    and supports loading from a string, dictionary, file path, or URL. The loader checks
    the manifest's format and its top-level keys, so that a manifest with invalid syntax or
    structure gets a more human readable error message than Pydantic's.

    **Usage Overview**

    The `SAMLoader` is intended to be subclassed for specific manifest types. It performs
    the following core functions:

    - **Manifest Acquisition**: Accepts manifest data in various forms, including a raw string,
      a Python dictionary, a file path, or a URL. Only one source should be provided at a time.
      The loader reads and stores the manifest data for further processing.

    - **Specification**: Keeps its own copy of a specification dictionary that describes the
      manifest's top-level keys and metadata, with the api version and kind filled in.
      :meth:`validate_manifest` does not read it; subclasses may.

    - **Format Detection**: Automatically detects whether the manifest data is in JSON or YAML
      format, and parses it accordingly. If the format is invalid or unsupported, an error is raised.

    - **Validation**: Checks that the manifest is a dict with the required top-level keys,
      ``apiVersion``, ``kind``, ``metadata`` and ``spec``. The values themselves are validated
      later, by the kind's Pydantic model. Validation errors are raised as exceptions.

    - **Extensibility**: Designed for subclassing, allowing child classes to override the
      specification and validation logic to accommodate custom manifest structures.

    **Manifest Structure**

    The expected manifest structure includes the following top-level keys:

    - `apiVersion`: The version of the Smarter API. Must be supported by the loader.
    - `kind`: The type of manifest. Can be specified directly or inferred from the manifest data.
    - `metadata`: A dictionary containing descriptive information such as name, description,
      version, tags, and annotations. Certain fields are required, while others are optional.
    - `spec`: The specification section, which is required and typically defined by subclasses.
    - `status`: An optional, read-only section for status information.

    **Validation Process**

    Upon initialization, the loader validates the manifest by:

    1. Ensuring the manifest data is present and in a supported format.
    2. Checking that the parsed manifest is a dict.
    3. Raising an error if any required top-level key is missing.

    **Subclassing**

    To support custom manifest types, create a subclass of `SAMLoader` and override the
    `_specification` attribute and the `validate_manifest` method as needed. This allows
    for the enforcement of additional keys, custom validation logic, and specialized
    handling of manifest data.

    **Error Handling**

    All validation and loading errors are raised as `SAMLoaderError` exceptions, providing
    clear feedback on the nature of the issue encountered.

    **Logging**

    The loader logs its state once it is initialized: at DEBUG when it is ready, and as a
    warning when it is not.
    """

    _api_version: str = SmarterApiVersions.V1
    _kind: Optional[str] = None
    _manifest: Optional[Union[str, SmarterDictType]] = None
    _file_path: Optional[str] = None
    _url: Optional[str] = None

    _raw_data: Optional[str] = None
    _dict_data: Optional[SmarterDictType] = None
    _data_format: Optional[SAMDataFormats] = None
    _specification: dict[SAMKeys, Any] = {
        SAMKeys.APIVERSION: SmarterApiVersions.V1,
        SAMKeys.KIND: "PLACEHOLDER",
        SAMKeys.METADATA: {
            SAMMetadataKeys.NAME: (str, [SAMSpecificationKeyOptions.REQUIRED]),
            SAMMetadataKeys.DESCRIPTION: (str, [SAMSpecificationKeyOptions.REQUIRED]),
            SAMMetadataKeys.VERSION: (str, [SAMSpecificationKeyOptions.REQUIRED]),
            SAMMetadataKeys.TAGS: (list, [SAMSpecificationKeyOptions.OPTIONAL]),
            SAMMetadataKeys.ANNOTATIONS: (list, [SAMSpecificationKeyOptions.OPTIONAL]),
        },
        SAMKeys.SPEC: (dict, [SAMSpecificationKeyOptions.REQUIRED]),
        SAMKeys.STATUS: (
            dict,
            [SAMSpecificationKeyOptions.READONLY, SAMSpecificationKeyOptions.OPTIONAL],
        ),
    }

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        *args,
        api_version: str = SmarterApiVersions.V1,
        kind: Optional[str] = None,
        manifest: Optional[Union[str, SmarterDictType]] = None,
        file_path: Optional[str] = None,
        url: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize a new instance of the :class:`SAMLoader`.

        This constructor is responsible for acquiring, parsing, and validating a Smarter API Manifest.
        It supports loading manifest data from several sources, but only one source should be provided at a time.

        :param api_version: The API version of the manifest. Must be one of the supported API versions.
        :param kind: The kind of manifest. If not provided, it will be inferred from the manifest data.
        :param manifest: The manifest data, provided as a JSON/YAML string or a Python dictionary.
        :param file_path: Path to a file containing the manifest data.
        :param url: URL pointing to the manifest data.

        :raises SAMLoaderError: If the API version is not supported, if no manifest source is provided,
            if multiple sources are provided, or if the manifest format is invalid.

        **Acquisition and Validation Process**

        1. The constructor checks that the provided API version is supported.
        2. It ensures that exactly one manifest source is specified (manifest, file_path, or url).
        3. The manifest data is loaded from the specified source.
        4. The loader sets the specification keys for API version and kind.
        5. The manifest is validated by :meth:`validate_manifest`, which checks its format and its required
           top-level keys.

        Child classes may override the specification and validation logic to support custom manifest structures.
        """
        self._api_version = api_version
        self._kind = kind
        self._manifest = manifest
        self._file_path = file_path
        self._url = url
        super().__init__(*args, **kwargs)
        if api_version not in SUPPORTED_API_VERSIONS:
            raise SAMLoaderError(f"Unsupported API version: {api_version}")

        # 1. acquire the manifest data
        # ---------------------------------------------------------------------
        if sum([bool(kind), bool(manifest), bool(file_path), bool(url)]) == 0:
            raise SAMLoaderError("One of kind, manifest, file_path, or url is required.")
        if sum([bool(manifest), bool(file_path), bool(url)]) > 1:
            raise SAMLoaderError("Only one of manifest, file_path, or url is allowed.")

        if manifest:
            if isinstance(manifest, str):
                # if manifest is a string, assume it's a JSON/YAML string
                self._raw_data = manifest
            elif isinstance(manifest, dict):
                self._raw_data = json.dumps(manifest)
            else:
                raise SAMLoaderError(f"Invalid manifest format. Expected JSON string or dict but got {type(manifest)}")
        elif file_path:
            with open(file_path, encoding="utf-8") as file:
                self._raw_data = file.read()
        elif url:
            self._raw_data = requests.get(url, timeout=30).text

        # 2. set specification key values, in this loader's own copy of the class's specification.
        self._specification = copy.deepcopy(type(self)._specification)
        self._specification[SAMKeys.APIVERSION] = api_version
        if kind:
            self._specification[SAMKeys.KIND] = kind
        else:
            self._specification[SAMKeys.KIND] = self.get_key(SAMKeys.KIND.value)

        # 3. validate the manifest's format and its required top-level keys.
        # ---------------------------------------------------------------------
        # Child classes may override validate_manifest() to check more. The
        # values themselves are validated by the kind's Pydantic model.
        self.validate_manifest()
        self.log_loader_state()

    def __str__(self) -> str:
        return f"{self.formatted_class_name}[{id(self)}](kind={self.kind}, name={self.name}, source={self.source})"

    def __repr__(self) -> str:
        return self.__str__()

    # -------------------------------------------------------------------------
    # data setters and getters. Sort out whether we received JSON or YAML data
    # -------------------------------------------------------------------------
    @property
    def api_version(self) -> str:
        """The manifest's ``apiVersion``, or the api version this loader was created with."""
        return self.manifest_api_version or self._api_version

    @property
    def kind(self) -> str:
        """The manifest's ``kind``, or the kind this loader was created with, or ``unknown-kind``."""
        manifest_kind = self.manifest_kind
        if manifest_kind:
            return manifest_kind
        if self._kind:
            return self._kind
        return "unknown-kind"

    @property
    def manifest(self) -> Optional[Union[str, SmarterDictType]]:
        """
        The manifest this loader was created with, or None if it is not a string or a dict.

        An invalid type is logged as an error.
        """
        if self._manifest is not None and not isinstance(self._manifest, (str, dict)):
            logger.error(
                "%s.manifest() - integrity error. Invalid manifest type: %s",
                self.formatted_class_name,
                type(self._manifest),
            )
            return None
        return self._manifest

    @property
    def file_path(self) -> Optional[str]:
        """The path of the manifest file this loader was created with, if any."""
        return self._file_path

    @property
    def url(self) -> Optional[str]:
        """The url of the manifest this loader was created with, if any."""
        return self._url

    @property
    def name(self) -> str:
        """The manifest's ``metadata.name``, or ``unknown-name``."""
        if self.manifest_metadata:
            return self.manifest_metadata.get(SAMMetadataKeys.NAME.value, "unknown-name")
        return "unknown-name"

    @property
    def source(self) -> str:
        """Describe where the manifest came from (manifest, file path or url), for log messages."""
        if self.manifest is not None:
            return "manifest " + type(self.manifest).__name__
        if self.file_path:
            return "file_path " + self.file_path
        if self.url:
            return "url " + self.url
        return "unknown-source"

    @property
    def specification(self) -> dict[SAMKeys, Any]:
        """The specification of required manifest keys that the manifest is validated against."""
        return self._specification

    @property
    def raw_data(self) -> Optional[Union[str, SmarterDictType]]:
        """The manifest data as loaded: a JSON or YAML string, or a dict."""
        return self._raw_data

    @property
    def json_data(self) -> Optional[SmarterDictType]:
        """
        The manifest data parsed into a dict, or None if its format is unknown.

        A YAML string is parsed once, by :attr:`data_format`, and the dict is kept: every key
        lookup reads this property.
        """
        data_format = self.data_format
        if data_format == SAMDataFormats.JSON:
            if isinstance(self.raw_data, str):
                return json.loads(self.raw_data)
            return self.raw_data
        if data_format == SAMDataFormats.YAML:
            if not isinstance(self.raw_data, str):
                return self.raw_data
            if self._dict_data is None:
                self._dict_data = yaml.safe_load(self.raw_data)
            return self._dict_data
        return None

    @property
    def yaml_data(self) -> Optional[str]:
        """The manifest data as a YAML string, or None if its format is unknown."""
        if self.data_format == SAMDataFormats.YAML:
            if isinstance(self.raw_data, str):
                return self.raw_data
            return yaml.dump(self.json_data)
        if self.data_format == SAMDataFormats.JSON:
            return yaml.dump(self.json_data)
        return None

    @property
    def data_format(self) -> SAMDataFormats:
        """
        Detect, and cache, whether the manifest data is JSON or YAML.

        A JSON string is parsed, and replaces the raw data.

        :returns: The data format, or ``SAMDataFormats.UNKNOWN`` if there is no data.
        :raises SAMLoaderError: If the data is neither JSON nor YAML.
        """
        if self._data_format:
            return self._data_format
        if not self.raw_data:
            return SAMDataFormats.UNKNOWN
        if isinstance(self.raw_data, dict):
            # we are a json dict
            self._data_format = SAMDataFormats.JSON
        else:
            try:
                # we are a json string, so convert to dict
                json_data = json.loads(self.raw_data)
                self._raw_data = json_data
                self._data_format = SAMDataFormats.JSON
            except json.JSONDecodeError:
                try:
                    # we are a yaml string. The parsed data is kept for json_data.
                    self._dict_data = yaml.safe_load(self.raw_data)
                    self._data_format = SAMDataFormats.YAML
                except yaml.YAMLError as e:
                    raise SAMLoaderError("Invalid data format. Supported formats: json, yaml") from e
        if not self._data_format:
            return SAMDataFormats.UNKNOWN
        return self._data_format

    @property
    def formatted_data(self) -> str:
        """The manifest data as a JSON string."""
        return json.dumps(self.json_data)

    def pydantic_model_dump(self) -> SmarterDictType:
        """
        Return a dictionary representation of the manifest data suitable for use with Pydantic models.

        This method produces a dictionary that can be directly passed as keyword arguments to any
        descendant of the ``AbstractSAMBase`` class. This enables seamless integration with Pydantic-based
        data validation and serialization workflows.

        The returned dictionary includes the following keys:

        - ``apiVersion``: The API version of the manifest.
        - ``kind``: The kind of manifest.
        - ``metadata``: The manifest metadata section.
        - ``spec``: The manifest specification section.
        - ``status``: The manifest status section.

        Example usage::

            SAMObject(**loader.pydantic_model_dump())

        :return: Dictionary representation of the manifest data, suitable for Pydantic model instantiation.
        """
        return {
            SAMKeys.APIVERSION.value: self.manifest_api_version,
            SAMKeys.KIND.value: self.manifest_kind,
            SAMKeys.METADATA.value: self.manifest_metadata,
            SAMKeys.SPEC.value: self.manifest_spec,
            SAMKeys.STATUS.value: self.manifest_status,
        }

    # -------------------------------------------------------------------------
    # class methods
    # -------------------------------------------------------------------------
    def get_key(self, key: str) -> Any:
        """
        Get a key from the manifest's JSON data.

        :param key: The key to retrieve.
        :return: The value of the key, or None if the key does not exist, or the manifest data is not a dict.
        """
        try:
            json_data = self.json_data
            if not isinstance(json_data, dict):
                return None
            return json_data[key]
        except (KeyError, TypeError):
            return None

    def validate_manifest(self) -> None:
        """
        Validate the manifest data.

        It checks the manifest's structure only. Its values are validated later, by the kind's
        Pydantic model, so a wrong data type or value is not reported here.

        The validation process includes the following steps:

        1. If the manifest data is empty, it logs a warning and returns, without raising.
        2. Ensures that the manifest data is in a supported format (JSON or YAML).
        3. Ensures that the parsed manifest is a dict.
        4. Ensures that it has the required top-level keys: ``apiVersion``, ``kind``, ``metadata`` and ``spec``.
        5. Raises a ``SAMLoaderError`` with a descriptive message if any of these checks fails.

        This method is intended to be called automatically during loader initialization, but can also be invoked manually
        to re-validate the manifest after modifications.

        Subclasses may override this method to implement additional or custom validation logic as needed.

        :raises SAMLoaderError: If the manifest data is in an unsupported format, is not a dict, or is missing
            a required top-level key.
        """

        # top-level validations of the manifest itself.
        if not self.raw_data:
            logger.warning("%s.validate_manifest() Received empty or invalid data.", self.formatted_class_name)
            return None
        if self.data_format not in [SAMDataFormats.JSON, SAMDataFormats.YAML]:
            raise SAMLoaderError("Invalid data format. Supported formats: json, yaml")

        if not isinstance(self.json_data, dict):
            raise SAMLoaderError(f"Invalid data format. Expected dict but got {type(self.json_data)}")

        if SAMKeys.APIVERSION.value not in self.json_data:
            raise SAMLoaderError(f"Missing required key: {SAMKeys.APIVERSION.value}")
        if SAMKeys.KIND.value not in self.json_data:
            raise SAMLoaderError(f"Missing required key: {SAMKeys.KIND.value}")
        if SAMKeys.METADATA.value not in self.json_data:
            raise SAMLoaderError(f"Missing required key: {SAMKeys.METADATA.value}")
        if SAMKeys.SPEC.value not in self.json_data:
            raise SAMLoaderError(f"Missing required key: {SAMKeys.SPEC.value}")

        # mcdaniel 2026-03-14: this has outlived its usefulness. Deprecating.
        # recursively validate the json representation of the manifest data
        # recursive_validator()

    # -------------------------------------------------------------------------
    # manifest properties
    # -------------------------------------------------------------------------
    @property
    def manifest_metadata_keys(self) -> list[str]:
        """
        Returns a list of all metadata keys defined in the SAMMetadataKeys enumeration.

        :return: A list of metadata key strings.
        """
        return SAMMetadataKeys.all()

    @property
    def manifest_spec_keys(self) -> list[str]:
        """
        Returns the keys of the manifest's ``spec``: none, here.

        This should be overridden by child classes to provide the specific spec keys
        relevant to their manifest type.

        :return: A list of spec key strings, empty here.
        """
        return []

    @property
    def manifest_status_keys(self) -> list[str]:
        """
        Returns the keys of the manifest's ``status``: none, here.

        This should be overridden by child classes to provide the specific status keys
        relevant to their manifest type.

        :return: A list of status key strings, empty here.
        """
        return []

    @property
    def manifest_api_version(self) -> Optional[str]:
        """
        Returns the API version of the manifest.

        :return: The API version string, or None if the manifest has none.
        """
        return self.get_key(SAMKeys.APIVERSION.value)

    @property
    def manifest_kind(self) -> Optional[str]:
        """
        Returns the kind of the manifest.

        :return: The kind string, or None if the manifest has none.
        """
        kind = self.get_key(SAMKeys.KIND.value)
        return kind

    @property
    def manifest_metadata(self) -> Optional[SmarterDictType]:
        """
        Returns the metadata section of the manifest.

        :return: The metadata dictionary, or None if the manifest has none.
        """
        return self.get_key(SAMKeys.METADATA.value)

    @property
    def manifest_spec(self) -> Optional[SmarterDictType]:
        """
        Returns the spec section of the manifest.

        :return: The spec dictionary, or None if the manifest has none.
        """
        return self.get_key(SAMKeys.SPEC.value)

    @property
    def manifest_sections(self) -> SmarterDictType:
        """
        Returns the manifest's apiVersion, kind, metadata and spec, to validate a broker's SAM model with.

        A broker builds its manifest with ``SAMGuardrail.model_validate(self.loader.manifest_sections)``.
        A section that the manifest doesn't have is None, which the model's validation rejects.

        :return: A dictionary with the keys ``apiVersion``, ``kind``, ``metadata`` and ``spec``.
        """
        sections: SmarterDictType = {
            SAMKeys.APIVERSION.value: self.manifest_api_version,
            SAMKeys.KIND.value: self.manifest_kind,
            SAMKeys.METADATA.value: self.manifest_metadata,
            SAMKeys.SPEC.value: self.manifest_spec,
        }
        return sections

    @property
    def manifest_status(self) -> Optional[SmarterDictType]:
        """
        Returns the status section of the manifest.

        :return: The status dictionary, or None if the manifest has none.
        """
        return self.get_key(SAMKeys.STATUS.value)

    @property
    def ready(self) -> bool:
        """
        Returns whether the manifest is ready for use.

        This property returns ``True`` if the manifest has been successfully validated and is in a valid state.
        A manifest is considered ready if all required sections—API version, kind, metadata, and spec—are present
        and non-empty. This property is useful for checking the readiness of a manifest before attempting to use
        it in downstream processes or integrations.

        :return: ``True`` if the manifest is valid and ready to be used, otherwise ``False``.
        """
        return (
            bool(self.manifest_api_version)
            and bool(self.manifest_kind)
            and bool(self.manifest_metadata)
            and bool(self.manifest_spec)
        )

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the class name formatted for logging.

        :return: The formatted class name as a string.
        """
        class_name = f"{__name__}.{SAMLoader.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def loader_ready_state(self) -> str:
        """
        Returns a string representation of the loader's readiness state.

        :return: "ready" if the loader is ready, otherwise "not ready".
        """
        if self.ready:
            return self.formatted_state_ready
        return self.formatted_state_not_ready

    def log_loader_state(self) -> None:
        """Log the current state of the SAMLoader instance: at DEBUG if it is ready, otherwise as a warning."""
        if self.ready:
            log = logger.debug
        else:
            log = logger.warning
        log(
            "%s.log_loader_state() %s %s loader is %s. source=%s",
            self.formatted_class_name,
            self.manifest_kind,
            self.name,
            self.loader_ready_state(),
            self.source,
        )

    def to_json(self) -> SmarterDictType:
        """
        Return the manifest data as a dict, with its keys sorted, for logging.

        :return: The manifest data, as a sorted dict.
        """
        return self.sorted_dict(self.json_data)  # type: ignore
