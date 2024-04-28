"""Smarter API Manifest ("SAM") base class."""

import json
import logging
from enum import Enum
from typing import Any

import requests
import waffle
import yaml

# pylint: disable=E0611
from smarter.common.classes import SmarterEnumAbstract
from smarter.common.exceptions import SAMValidationError


logger = logging.getLogger(__name__)

SMARTER_API_VERSION = "smarter/v0"


class SAMDataFormats(SmarterEnumAbstract):
    """Data format enumeration."""

    JSON = "json"
    YAML = "yaml"


class SAMSpecificationKeyOptions(SmarterEnumAbstract):
    """Key types enumeration."""

    REQUIRED = "required"
    OPTIONAL = "optional"
    READONLY = "readonly"


class SAMKinds(SmarterEnumAbstract):
    """Smarter manifest kinds enumeration."""

    PLUGIN = "Plugin"
    ACCOUNT = "Account"
    USER = "User"
    CHAT = "Chat"
    CHATBOT = "Chatbot"


class SAMKeys(SmarterEnumAbstract):
    """Smarter API V0 required keys enumeration."""

    APIVERSION = "apiVersion"
    KIND = "kind"
    METADATA = "metadata"
    SPEC = "spec"
    STATUS = "status"


class SAMMetadataKeys(SmarterEnumAbstract):
    """Smarter API V0 Plugin Metadata keys enumeration."""

    NAME = "name"
    DESCRIPTION = "description"
    VERSION = "version"
    TAGS = "tags"
    ANNOTATIONS = "annotations"


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
        raise SAMValidationError(f"Invalid data type for key {key}. Expected str but got {type(key)}")

    # validate that key's value exists in the spec list
    if isinstance(spec, list):
        if key_value not in spec:
            raise SAMValidationError(f"Invalid value {key_value} for key {key}. Expected one of {spec}")

    # validate that key value's data type matches the spec's data type, and if required, that the key exists
    elif isinstance(spec, tuple):
        type_spec = spec[0]
        options_list = spec[1]
        # validate that value exists for required key
        if SAMSpecificationKeyOptions.REQUIRED in options_list and not key_value:
            raise SAMValidationError(f"Missing required key {key}")
        if not SAMSpecificationKeyOptions.OPTIONAL and not isinstance(key_value, type_spec):
            raise SAMValidationError(
                f"Invalid data type for key {key}. Expected {spec[0]} but got {type(key_value)}: key_value={key_value} spec={spec[0]}"
            )

    # validate that key value is the same as the spec value
    else:
        if not isinstance(key_value, type(spec)):
            # possibility #1: the data is missing, so it's a NoneType
            if key_value is None:
                raise SAMValidationError(f"Missing required key {key}")
            # possibility #2: the data exists but is the wrong type
            raise SAMValidationError(
                f"Invalid key_value type for key {key}. Expected {type(spec)} but got {type(key_value)}"
            )
        if key_value != spec:
            raise SAMValidationError(f"Invalid value for key {key}. Expected {spec} but got {key_value}")


class SAM:
    """
    Smarter API Manifest ("SAM") base class.
    """

    _raw_data: str = None
    _dict_data: dict = None
    _data_format: SAMDataFormats = None
    _specification: dict = None

    def __init__(
        self,
        manifest: str = None,
        data_format: SAMDataFormats = None,
        file_path: str = None,
        url: str = None,
    ):
        self._specification = {
            SAMKeys.APIVERSION: SMARTER_API_VERSION,
            SAMKeys.KIND: SAMKinds.all_values(),
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

        self._raw_data = manifest
        if data_format:
            if data_format == SAMDataFormats.JSON:
                try:
                    json.loads(manifest)
                except json.JSONDecodeError as e:
                    raise SAMValidationError("Invalid json data received.") from e
            elif data_format == SAMDataFormats.YAML:
                try:
                    yaml.safe_load(manifest)
                except yaml.YAMLError as e:
                    raise SAMValidationError("Invalid yaml data received.") from e
            else:
                raise SAMValidationError("Supported data formats: json, yaml.")
            self._data_format = data_format

        if not manifest and file_path:
            with open(file_path, encoding="utf-8") as file:
                self._raw_data = file.read()
        elif not manifest and url:
            self._raw_data = requests.get(url, timeout=30).text

        self.validate()

    # -------------------------------------------------------------------------
    # data setters and getters. Sort out whether we received JSON or YAML data
    # -------------------------------------------------------------------------
    @property
    def specification(self) -> dict:
        return self._specification

    @property
    def raw_data(self) -> str:
        return self._raw_data

    @property
    def json_data(self) -> dict:
        try:
            return json.loads(self.raw_data)
        except json.JSONDecodeError:
            return None

    @property
    def yaml_data(self) -> str:
        try:
            data = yaml.safe_load(self.raw_data)
            if isinstance(data, dict):
                return data
        except yaml.YAMLError:
            pass
        return None

    @property
    def data_format(self) -> SAMDataFormats:
        if self._data_format:
            return self._data_format
        if self.json_data:
            self._data_format = SAMDataFormats.JSON
        elif self.yaml_data:
            self._data_format = SAMDataFormats.YAML
        return self._data_format

    @property
    def data(self) -> dict:
        if self._dict_data:
            return self._dict_data
        if self.data_format == SAMDataFormats.JSON:
            self._dict_data = self.json_data
        elif self.data_format == SAMDataFormats.YAML:
            self._dict_data = self.yaml_data
        return self._dict_data

    @property
    def formatted_data(self) -> str:
        return json.dumps(self.data, indent=4)

    # -------------------------------------------------------------------------
    # class methods
    # -------------------------------------------------------------------------
    def get_key(self, key) -> any:
        try:
            return self.data[key]
        except KeyError:
            pass
        return None

    def validate(self):
        """
        Validate the manifest data. Recursively validate dict keys based on the
        contents of spec.
        """
        # top-level validations of the manifest itself.
        if not self.raw_data:
            raise SAMValidationError("Received empty or invalid data.")
        if not self.data:
            raise SAMValidationError("Invalid data format. Supported formats: json, yaml")

        def recursive_validator(recursed_data: dict = None, recursed_spec: dict = None):
            this_overall_spec = recursed_spec or self.specification
            this_data = recursed_data or self.data
            if not this_data:
                raise SAMValidationError("Received empty or invalid data.")

            for key, key_spec in this_overall_spec.items():
                if isinstance(key, Enum):
                    key = key.value
                key_value = this_data.get(key)
                if isinstance(key_spec, dict):
                    if waffle.switch_is_active("manifest_logging"):
                        logger.info("recursing to key %s with spec %s using data %s", key, key_spec, key_value)
                    recursive_validator(recursed_data=key_value, recursed_spec=key_spec)
                else:
                    if waffle.switch_is_active("manifest_logging"):
                        logger.info("Validating key %s with spec %s using data %s", key, key_spec, key_value)
                    validate_key(
                        key=key,
                        key_value=key_value,
                        spec=key_spec,
                    )

        recursive_validator()

    # -------------------------------------------------------------------------
    # manifest properties
    # -------------------------------------------------------------------------
    @property
    def manifest_api_version(self) -> str:
        return self.get_key(SAMKeys.APIVERSION.value)

    @property
    def manifest_kind(self) -> str:
        return self.get_key(SAMKeys.KIND.value)

    @property
    def manifest_metadata_keys(self) -> list[str]:
        return SAMMetadataKeys.all_values()

    @property
    def manifest_spec_keys(self) -> list[str]:
        return []

    @property
    def manifest_status_keys(self) -> list[str]:
        return []

    def manifest_metadata(self, key: str = None) -> any:
        meta_data = self.get_key(SAMKeys.METADATA.value)
        if key in SAMMetadataKeys.all_values():
            return meta_data.get(key)
        return meta_data

    def manifest_spec(self, key: str = None) -> any:
        spec_data = self.get_key(SAMKeys.SPEC.value)
        if key:
            return spec_data.get(key)
        return spec_data

    def manifest_status(self, key: str = None) -> any:
        status_data = self.get_key(SAMKeys.STATUS.value)
        if key:
            return status_data.get(key)
        return status_data
