"""Smarter API Manifest Loader base class."""

import json
import logging
from enum import Enum
from typing import Any, Union

import requests
import yaml

from smarter.common.api import SmarterApiVersions
from smarter.common.classes import SmarterHelperMixin

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
    """

    _raw_data: str = None
    _dict_data: dict = None
    _data_format: SAMDataFormats = None
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
        kind: str = None,
        manifest: str = None,
        file_path: str = None,
        url: str = None,
    ):
        if api_version not in SUPPORTED_API_VERSIONS:
            raise SAMLoaderError(f"Unsupported API version: {api_version}")

        # 1. acquire the manifest data
        # ---------------------------------------------------------------------
        if sum([bool(kind), bool(manifest), bool(file_path), bool(url)]) == 0:
            raise SAMLoaderError("One of kind, manifest, file_path, or url is required.")
        if sum([bool(manifest), bool(file_path), bool(url)]) > 1:
            raise SAMLoaderError("Only one of manifest, file_path, or url is allowed.")

        if manifest:
            self._raw_data = manifest
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

    # -------------------------------------------------------------------------
    # data setters and getters. Sort out whether we received JSON or YAML data
    # -------------------------------------------------------------------------
    @property
    def specification(self) -> dict:
        return self._specification

    @property
    def raw_data(self) -> Union[str, dict]:
        return self._raw_data

    @property
    def json_data(self) -> dict:
        if self.data_format == SAMDataFormats.JSON:
            return self.raw_data
        if self.data_format == SAMDataFormats.YAML:
            return yaml.safe_load(self.raw_data)
        return None

    @property
    def yaml_data(self) -> str:
        if self.data_format == SAMDataFormats.YAML:
            return self.raw_data
        if self.data_format == SAMDataFormats.JSON:
            return yaml.dump(self.json_data)
        return None

    @property
    def data_format(self) -> SAMDataFormats:
        if self._data_format:
            return self._data_format
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
        return self._data_format

    @property
    def formatted_data(self) -> str:
        return json.dumps(self.json_data, indent=4)

    def pydantic_model_dump(self) -> dict:
        """
        Returns a Pydantic model of the manifest data. This *SHOULD* be
        readable by any descedent of the AbstractSAMBase class using
        this syntax:
            `SAMObject(**loader.pydantic_model_dump())`
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
    def get_key(self, key) -> any:
        try:
            return self.json_data[key]
        except KeyError:
            return None

    def validate_manifest(self):
        """
        Validate the manifest data. Recursively validate dict keys based on the
        contents of spec.
        """

        def recursive_validator(recursed_data: dict = None, recursed_spec: dict = None):
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
        if not self.data_format:
            raise SAMLoaderError("Invalid data format. Supported formats: json, yaml")
        # recursively validate the json representation of the manifest data
        recursive_validator()

    # -------------------------------------------------------------------------
    # manifest properties
    # -------------------------------------------------------------------------
    @property
    def manifest_metadata_keys(self) -> list[str]:
        return SAMMetadataKeys.all_values()

    @property
    def manifest_spec_keys(self) -> list[str]:
        return []

    @property
    def manifest_status_keys(self) -> list[str]:
        return []

    @property
    def manifest_api_version(self) -> str:
        return self.get_key(SAMKeys.APIVERSION.value)

    @property
    def manifest_kind(self) -> str:
        if not self._specification[SAMKeys.KIND]:
            self._specification[SAMKeys.KIND] = self.get_key(SAMKeys.KIND.value)
        return self.get_key(SAMKeys.KIND.value)

    @property
    def manifest_metadata(self) -> dict:
        return self.get_key(SAMKeys.METADATA.value)

    @property
    def manifest_spec(self) -> dict:
        return self.get_key(SAMKeys.SPEC.value)

    @property
    def manifest_status(self) -> dict:
        return self.get_key(SAMKeys.STATUS.value)
