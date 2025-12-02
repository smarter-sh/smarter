"""Smarter API Manifest Loader base class."""

import logging
from enum import Enum
from typing import Any, Optional, Union

import requests
import yaml

from smarter.common.api import SmarterApiVersions
from smarter.common.classes import SmarterHelperMixin
from smarter.lib import json

from .enum import SAMDataFormats, SAMKeys, SAMMetadataKeys, SAMSpecificationKeyOptions
from .exceptions import SAMExceptionBase


logger = logging.getLogger(__name__)

SUPPORTED_API_VERSIONS = [SmarterApiVersions.V1]


class SAMLoaderError(SAMExceptionBase):
    """Base class for all SAMLoader errors."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Manifest Loader Error"


def validate_key(key: str, key_value: Any, spec: Any):
    """
    Validate a key against a spec. Of note:
    - If a key's value is a list then validate the value of the key against the list
    - If a key's value is a tuple then validate the value of the key against the tuple, as follows:
        - The first element of the tuple is the expected data type
        - The second element of the tuple is the key type (required, optional, readonly)
    - otherwise, validate the value of the key against spec value
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
        if not SAMSpecificationKeyOptions.OPTIONAL and not isinstance(key_value, type_spec):
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
    Smarter API Manifest files. It is designed to handle manifests provided as JSON or YAML,
    and supports loading from a string, dictionary, file path, or URL. The loader ensures
    that the manifest conforms to a specified schema, validating both the structure and
    the data types of the manifest's contents.

    **Usage Overview**

    The `SAMLoader` is intended to be subclassed for specific manifest types. It performs
    the following core functions:

    - **Manifest Acquisition**: Accepts manifest data in various forms, including a raw string,
      a Python dictionary, a file path, or a URL. Only one source should be provided at a time.
      The loader reads and stores the manifest data for further processing.

    - **Specification Enforcement**: Maintains a specification dictionary that defines the
      required structure and data types for the manifest. This includes top-level keys such as
      API version, kind, metadata, spec, and status, as well as nested metadata requirements.

    - **Format Detection**: Automatically detects whether the manifest data is in JSON or YAML
      format, and parses it accordingly. If the format is invalid or unsupported, an error is raised.

    - **Validation**: Recursively validates the manifest data against the specification. This
      includes checking for required keys, verifying data types, and ensuring that values conform
      to enumerated options where applicable. Validation errors are raised as exceptions.

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
    2. Recursively checking each key and value against the specification.
    3. Raising detailed errors if any required keys are missing, data types are incorrect,
       or values are invalid.

    **Subclassing**

    To support custom manifest types, create a subclass of `SAMLoader` and override the
    `_specification` attribute and the `validate_manifest` method as needed. This allows
    for the enforcement of additional keys, custom validation logic, and specialized
    handling of manifest data.

    **Error Handling**

    All validation and loading errors are raised as `SAMLoaderError` exceptions, providing
    clear feedback on the nature of the issue encountered.

    **Logging**

    The loader uses Python's standard logging library to emit warnings and errors during
    the validation process, aiding in debugging and traceability.

    """

    _raw_data: Optional[str] = None
    _dict_data: Optional[dict] = None
    _data_format: Optional[SAMDataFormats] = None
    _specification: dict = {
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
        api_version: str = SmarterApiVersions.V1,
        kind: Optional[str] = None,
        manifest: Optional[Union[str, dict]] = None,
        file_path: Optional[str] = None,
        url: Optional[str] = None,
    ):
        """
        Initialize a new instance of the :class:`SAMLoader`.

        This constructor is responsible for acquiring, parsing, and validating a Smarter API Manifest.
        It supports loading manifest data from several sources, but only one source should be provided at a time.

        :param api_version: The API version of the manifest. Must be one of the supported API versions.
        :type api_version: str
        :param kind: The kind of manifest. If not provided, it will be inferred from the manifest data.
        :type kind: str, optional
        :param manifest: The manifest data, provided as a JSON/YAML string or a Python dictionary.
        :type manifest: str or dict, optional
        :param file_path: Path to a file containing the manifest data.
        :type file_path: str, optional
        :param url: URL pointing to the manifest data.
        :type url: str, optional

        :raises SAMLoaderError: If the API version is not supported, if no manifest source is provided,
            if multiple sources are provided, or if the manifest format is invalid.

        **Acquisition and Validation Process**

        1. The constructor checks that the provided API version is supported.
        2. It ensures that exactly one manifest source is specified (manifest, file_path, or url).
        3. The manifest data is loaded from the specified source.
        4. The loader sets the specification keys for API version and kind.
        5. The manifest is validated against the specification, checking for required keys and correct data types.

        Child classes may override the specification and validation logic to support custom manifest structures.
        """
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

        # 2. set specification key values
        self._specification[SAMKeys.APIVERSION] = api_version
        if kind:
            self._specification[SAMKeys.KIND] = kind
        else:
            self._specification[SAMKeys.KIND] = self.get_key(SAMKeys.KIND.value)

        # 3. validate a json representation of the manifest using our in-house Enumerated data types.
        # ---------------------------------------------------------------------
        # Note that child classes are expected to
        # override the specification as well as validate() in order to add
        # the specification details of their own individual manifests.
        # Therefore, this call will only validate the top-level keys and values
        # of the manifest.
        self.validate_manifest()

    def __str__(self):
        return self.formatted_class_name + f"({self.manifest_api_version}, {self.manifest_kind})"

    # -------------------------------------------------------------------------
    # data setters and getters. Sort out whether we received JSON or YAML data
    # -------------------------------------------------------------------------
    @property
    def specification(self) -> dict:
        return self._specification

    @property
    def raw_data(self) -> Optional[Union[str, dict]]:
        return self._raw_data

    @property
    def json_data(self) -> Optional[dict[str, Any]]:
        if self.data_format == SAMDataFormats.JSON:
            return json.loads(self.raw_data) if isinstance(self.raw_data, str) else self.raw_data
        if self.data_format == SAMDataFormats.YAML:
            return yaml.safe_load(self.raw_data) if isinstance(self.raw_data, str) else self.raw_data
        return None

    @property
    def yaml_data(self) -> Optional[str]:
        if self.data_format == SAMDataFormats.YAML:
            return self.raw_data if isinstance(self.raw_data, str) else yaml.dump(self.json_data)
        if self.data_format == SAMDataFormats.JSON:
            return yaml.dump(self.json_data)
        return None

    @property
    def data_format(self) -> SAMDataFormats:
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
                    # we are a yaml string
                    yaml.safe_load(self.raw_data)
                    self._data_format = SAMDataFormats.YAML
                except yaml.YAMLError as e:
                    raise SAMLoaderError("Invalid data format. Supported formats: json, yaml") from e
        if not self._data_format:
            return SAMDataFormats.UNKNOWN
        return self._data_format

    @property
    def formatted_data(self) -> str:
        return json.dumps(self.json_data)

    def pydantic_model_dump(self) -> dict:
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
        :rtype: dict
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
    def get_key(self, key) -> Any:
        """
        Get a key from the manifest's JSON data.

        :param key: The key to retrieve.
        :type key: str
        :return: The value of the key, or None if the key does not exist.
        :rtype: Any
        """
        try:
            return self.json_data[key] if isinstance(self.json_data, dict) else None
        except (KeyError, TypeError):
            return None

    def validate_manifest(self):
        """
        Validate the manifest data.

        This method performs a comprehensive validation of the manifest data against the expected specification.
        Validation is performed recursively, ensuring that all required keys are present, that values are of the correct
        data types, and that any enumerated or restricted values are respected. The validation process is driven by the
        specification dictionary defined for the loader, which outlines the required structure and constraints for the manifest.

        The validation process includes the following steps:

        1. Checks that the manifest data is present and not empty.
        2. Ensures that the manifest data is in a supported format (JSON or YAML).
        3. Recursively traverses the manifest data, validating each key and value against the corresponding entry in the specification.
        4. For each key:
           - If the specification entry is a dictionary, validation is performed recursively on the nested structure.
           - If the specification entry is a tuple, the method checks for required keys, correct data types, and any special options (such as optional or read-only).
           - If the specification entry is a list, the method checks that the value is one of the allowed options.
           - Otherwise, the method checks for exact value and type matches.
        5. Raises a ``SAMLoaderError`` with a descriptive message if any validation check fails.

        This method is intended to be called automatically during loader initialization, but can also be invoked manually
        to re-validate the manifest after modifications.

        Subclasses may override this method to implement additional or custom validation logic as needed.

        :raises SAMLoaderError: If the manifest data is missing, in an unsupported format, or fails validation.
        """

        def recursive_validator(recursed_data: Optional[dict] = None, recursed_spec: Optional[dict] = None):
            this_overall_spec = recursed_spec or self.specification
            this_data = recursed_data or self.json_data
            if not this_data:
                raise SAMLoaderError("Received empty or invalid data.")
            if not isinstance(this_data, dict):
                raise SAMLoaderError(f"Invalid data format. Expected dict but got {type(this_data)}")

            for key, key_spec in this_overall_spec.items():
                if isinstance(key, Enum):
                    key = key.value
                key_value = this_data.get(key)
                if isinstance(key_spec, dict):
                    recursive_validator(recursed_data=key_value, recursed_spec=key_spec)
                else:
                    validate_key(
                        key=key,
                        key_value=key_value,
                        spec=key_spec,
                    )

        # top-level validations of the manifest itself.
        if not self.raw_data:
            logger.warning("%s.validate_manifest() Received empty or invalid data.", self.formatted_class_name)
            return None
        if not self.data_format in [SAMDataFormats.JSON, SAMDataFormats.YAML]:
            raise SAMLoaderError("Invalid data format. Supported formats: json, yaml")
        # recursively validate the json representation of the manifest data
        recursive_validator()

    # -------------------------------------------------------------------------
    # manifest properties
    # -------------------------------------------------------------------------
    @property
    def manifest_metadata_keys(self) -> list[str]:
        """
        Returns a list of all metadata keys defined in the SAMMetadataKeys enumeration.

        :return: A list of metadata key strings.
        :rtype: list[str]
        """
        return SAMMetadataKeys.all_values()

    @property
    def manifest_spec_keys(self) -> list[str]:
        """
        Returns a list of all spec keys defined in the SAMSpecKeys enumeration.
        This should be overridden by child classes to provide the specific spec keys
        relevant to their manifest type.

        :return: A list of spec key strings.
        :rtype: list[str]
        """
        return []

    @property
    def manifest_status_keys(self) -> list[str]:
        """
        Returns a list of all status keys defined in the SAMStatusKeys enumeration.
        This should be overridden by child classes to provide the specific status keys
        relevant to their manifest type.

        :return: A list of status key strings.
        :rtype: list[str]
        """
        return []

    @property
    def manifest_api_version(self) -> str:
        """
        Returns the API version of the manifest.

        :return: The API version string.
        :rtype: str
        """
        return self.get_key(SAMKeys.APIVERSION.value)

    @property
    def manifest_kind(self) -> str:
        """
        Returns the kind of the manifest.

        :return: The kind string.
        :rtype: str
        """
        if not self._specification[SAMKeys.KIND]:
            self._specification[SAMKeys.KIND] = self.get_key(SAMKeys.KIND.value)
        return self.get_key(SAMKeys.KIND.value)

    @property
    def manifest_metadata(self) -> dict:
        """
        Returns the metadata section of the manifest.

        :return: The metadata dictionary.
        :rtype: dict
        """
        return self.get_key(SAMKeys.METADATA.value)

    @property
    def manifest_spec(self) -> dict:
        """
        Returns the spec section of the manifest.

        :return: The spec dictionary.
        :rtype: dict
        """
        return self.get_key(SAMKeys.SPEC.value)

    @property
    def manifest_status(self) -> dict:
        """
        Returns the status section of the manifest.

        :return: The status dictionary.
        :rtype: dict
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
        :rtype: bool
        """
        return (
            bool(self.manifest_api_version)
            and bool(self.manifest_kind)
            and bool(self.manifest_metadata)
            and bool(self.manifest_spec)
        )
