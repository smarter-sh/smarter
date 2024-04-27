"""Top-level API classes for the Smarter API."""

import json
import logging
from enum import Enum
from typing import Any

import requests
import waffle
import yaml

from smarter.common.exceptions import SmarterApiManifestValidationError


logger = logging.getLogger(__name__)

SMARTER_API_VERSION = "smarter/v0"


class SmarterEnumAbstract(Enum):
    """Smarter manifest kinds enumeration."""

    @classmethod
    def all_values(cls) -> list[str]:
        return [member.value for _, member in cls.__members__.items()]


class SmarterApiManifestDataFormats(SmarterEnumAbstract):
    """Data format enumeration."""

    JSON = "json"
    YAML = "yaml"


class SmarterApiSpecificationKeyOptions(SmarterEnumAbstract):
    """Key types enumeration."""

    REQUIRED = "required"
    OPTIONAL = "optional"
    READONLY = "readonly"


class SmarterApiManifestKinds(SmarterEnumAbstract):
    """Smarter manifest kinds enumeration."""

    PLUGIN = "Plugin"
    ACCOUNT = "Account"
    USER = "User"
    CHAT = "Chat"
    CHATBOT = "Chatbot"


class SmarterApiManifestKeys(SmarterEnumAbstract):
    """Smarter API V0 required keys enumeration."""

    APIVERSION = "apiVersion"
    KIND = "kind"
    METADATA = "metadata"
    SPEC = "spec"
    STATUS = "status"


class SmarterApiManifestMetadataKeys(SmarterEnumAbstract):
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
        raise SmarterApiManifestValidationError(f"Invalid data type for key {key}. Expected str but got {type(key)}")

    # validate that key's value exists in the spec list
    if isinstance(spec, list):
        if key_value not in spec:
            raise SmarterApiManifestValidationError(f"Invalid value for key {key}")

    # validate that key value's data type matches the spec's data type, and if required, that the key exists
    elif isinstance(spec, tuple):
        type_spec = spec[0]
        options_list = spec[1]
        # validate that value exists for required key
        if SmarterApiSpecificationKeyOptions.REQUIRED in options_list and not key_value:
            raise SmarterApiManifestValidationError(f"Missing required key {key}")
        if not SmarterApiSpecificationKeyOptions.OPTIONAL and not isinstance(key_value, type_spec):
            raise SmarterApiManifestValidationError(
                f"Invalid data type for key {key}. Expected {spec[0]} but got {type(key_value)}: key_value={key_value} spec={spec[0]}"
            )

    # validate that key value is the same as the spec value
    else:
        if not isinstance(key_value, type(spec)):
            raise SmarterApiManifestValidationError(
                f"Invalid key_value type for key {key}. Expected {type(spec)} but got {type(key_value)}"
            )
        if key_value != spec:
            raise SmarterApiManifestValidationError(f"Invalid value for key {key}. Expected {spec} but got {key_value}")


class SmarterApiManifest:
    """
    Smarter API base class.
    """

    _raw_data: str = None
    _dict_data: dict = None
    _data_format: SmarterApiManifestDataFormats = None
    _specification: dict = None

    def __init__(
        self,
        manifest: str = None,
        data_format: SmarterApiManifestDataFormats = None,
        file_path: str = None,
        url: str = None,
    ):
        self._specification = {
            SmarterApiManifestKeys.APIVERSION: SMARTER_API_VERSION,
            SmarterApiManifestKeys.KIND: SmarterApiManifestKinds.all_values(),
            SmarterApiManifestKeys.METADATA: {
                SmarterApiManifestMetadataKeys.NAME: (str, [SmarterApiSpecificationKeyOptions.REQUIRED]),
                SmarterApiManifestMetadataKeys.DESCRIPTION: (str, [SmarterApiSpecificationKeyOptions.REQUIRED]),
                SmarterApiManifestMetadataKeys.VERSION: (str, [SmarterApiSpecificationKeyOptions.REQUIRED]),
                SmarterApiManifestMetadataKeys.TAGS: (list, [SmarterApiSpecificationKeyOptions.OPTIONAL]),
                SmarterApiManifestMetadataKeys.ANNOTATIONS: (list, [SmarterApiSpecificationKeyOptions.OPTIONAL]),
            },
            SmarterApiManifestKeys.SPEC: (dict, [SmarterApiSpecificationKeyOptions.REQUIRED]),
            SmarterApiManifestKeys.STATUS: (
                dict,
                [SmarterApiSpecificationKeyOptions.READONLY, SmarterApiSpecificationKeyOptions.OPTIONAL],
            ),
        }

        logger.info("SmarterApiManifest init spec: %s", self.specification)

        self._raw_data = manifest
        if data_format:
            if data_format == SmarterApiManifestDataFormats.JSON:
                try:
                    json.loads(manifest)
                except json.JSONDecodeError as e:
                    raise SmarterApiManifestValidationError("Invalid json data received.") from e
            elif data_format == SmarterApiManifestDataFormats.YAML:
                try:
                    yaml.safe_load(manifest)
                except yaml.YAMLError as e:
                    raise SmarterApiManifestValidationError("Invalid yaml data received.") from e
            else:
                raise SmarterApiManifestValidationError("Supported data formats: json, yaml.")
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
    def dict_data(self) -> dict:
        try:
            return json.loads(self.raw_data)
        except json.JSONDecodeError:
            return None

    @property
    def yaml_data(self) -> str:
        try:
            return yaml.safe_load(self.raw_data)
        except yaml.YAMLError:
            return None

    @property
    def data_format(self) -> SmarterApiManifestDataFormats:
        if self._data_format:
            return self._data_format
        if self.dict_data:
            self._data_format = SmarterApiManifestDataFormats.JSON
        elif self.yaml_data:
            self._data_format = SmarterApiManifestDataFormats.YAML
        return None

    @property
    def data(self) -> dict:
        if self._dict_data:
            return self._dict_data
        if self.data_format == SmarterApiManifestDataFormats.JSON:
            self._dict_data = self.dict_data
        elif self.data_format == SmarterApiManifestDataFormats.YAML:
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

    def validate(self, recursed_data: dict = None, recursed_spec: dict = None):
        """
        Validate the manifest data. Recursively validate dict keys based on the
        contents of spec.
        """
        logger.info("SmarterApiManifest validate() - 1: %s", self.specification)

        this_overall_spec = recursed_spec or self.specification
        this_data = recursed_data or self.data
        if not this_data:
            raise SmarterApiManifestValidationError("Received empty or invalid data.")

        for key, key_spec in this_overall_spec.items():
            if isinstance(key, Enum):
                key = key.value
            key_value = this_data.get(key)
            if isinstance(key_spec, dict):
                if waffle.switch_is_active("manifest_logging"):
                    logger.info("recursing to key %s with spec %s using data %s", key, key_spec, key_value)
                self.validate(recursed_data=key_value, recursed_spec=key_spec)
            else:
                if waffle.switch_is_active("manifest_logging"):
                    logger.info("Validating key %s with spec %s using data %s", key, key_spec, key_value)
                validate_key(
                    key=key,
                    key_value=key_value,
                    spec=key_spec,
                )

    # -------------------------------------------------------------------------
    # manifest properties
    # -------------------------------------------------------------------------
    @property
    def manifest_api_version(self) -> str:
        return self.get_key(SmarterApiManifestKeys.APIVERSION.value)

    @property
    def manifest_kind(self) -> str:
        return self.get_key(SmarterApiManifestKeys.KIND.value)

    @property
    def manifest_metadata_keys(self) -> list[str]:
        return SmarterApiManifestMetadataKeys.all_values()

    @property
    def manifest_spec_keys(self) -> list[str]:
        return []

    @property
    def manifest_status_keys(self) -> list[str]:
        return []

    def manifest_metadata(self, key: str = None) -> any:
        meta_data = self.get_key(SmarterApiManifestKeys.METADATA.value)
        if key in SmarterApiManifestMetadataKeys.all_values():
            return meta_data.get(key)
        return meta_data

    def manifest_spec(self, key: str = None) -> any:
        spec_data = self.get_key(SmarterApiManifestKeys.SPEC.value)
        if key:
            return spec_data.get(key)
        return spec_data

    def manifest_status(self, key: str = None) -> any:
        status_data = self.get_key(SmarterApiManifestKeys.STATUS.value)
        if key:
            return status_data.get(key)
        return status_data
