"""Top-level API classes for the Smarter API."""

import json
from abc import ABC
from enum import Enum
from typing import Any

import yaml

from smarter.common.exceptions import SmarterApiManifestValidationError


SMARTER_API_VERSION = "smarter/v0"


class SmarterEnumAbstract(Enum):
    """Smarter manifest kinds enumeration."""

    @classmethod
    def all_values(cls) -> list[str]:
        return [member.value for _, member in SmarterApiManifestKinds.__members__.items()]


class SmarterApiManifDataFormats(SmarterEnumAbstract):
    """Data format enumeration."""

    JSON = "json"
    YAML = "yaml"


class SmarterApiSpecKeyOptions(SmarterEnumAbstract):
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


def validate_key(key: str, spec: Any, data: dict):
    """
    Validate a key against a spec. Of note:
    - If a key's value is a list then validate the value of the key against the list
    - If a key's value is a tuple then validate the value of the key against the tuple, as follows:
        - The first element of the tuple is the expected data type
        - The second element of the tuple is the key type (required, optional, readonly)
    """
    if isinstance(spec, list):
        if data.get(key) not in spec:
            raise SmarterApiManifestValidationError(f"Invalid value for key {key}")
    elif isinstance(spec, tuple):
        if not isinstance(data.get(key), spec[0]):
            raise SmarterApiManifestValidationError(
                f"Invalid data type for key {key}. Expected {spec[0]} but got {type(data.get(key))}"
            )
        if spec[1] == SmarterApiSpecKeyOptions.REQUIRED and key not in data:
            raise SmarterApiManifestValidationError(f"Missing required key {key}")


class SmarterApi(ABC):
    """
    Smarter API base class.
    """

    _raw_data: str = None
    _dict_data: dict = None
    _data_format: SmarterApiManifDataFormats = None
    _spec = {
        SmarterApiManifestKeys.APIVERSION: SMARTER_API_VERSION,
        SmarterApiManifestKeys.KIND: SmarterApiManifestKinds.all_values(),
        SmarterApiManifestKeys.METADATA: (dict, [SmarterApiSpecKeyOptions.REQUIRED]),
        SmarterApiManifestKeys.SPEC: (dict, [SmarterApiSpecKeyOptions.REQUIRED]),
        SmarterApiManifestKeys.STATUS: (dict, [SmarterApiSpecKeyOptions.READONLY, SmarterApiSpecKeyOptions.OPTIONAL]),
    }

    def __init__(self, manifest: str, data_format: SmarterApiManifDataFormats = None):
        self._raw_data = manifest
        if data_format:
            if data_format == SmarterApiManifDataFormats.JSON:
                try:
                    json.loads(manifest)
                except json.JSONDecodeError as e:
                    raise SmarterApiManifestValidationError("Invalid json data received.") from e
            elif data_format == SmarterApiManifDataFormats.YAML:
                try:
                    yaml.safe_load(manifest)
                except yaml.YAMLError as e:
                    raise SmarterApiManifestValidationError("Invalid yaml data received.") from e
            else:
                raise SmarterApiManifestValidationError("Supported data formats: json, yaml.")
            self._data_format = data_format

        self.validate()

    # -------------------------------------------------------------------------
    # data setters and getters. Sort out whether we received JSON or YAML data
    # -------------------------------------------------------------------------
    @property
    def raw_data(self):
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
    def data_format(self) -> SmarterApiManifDataFormats:
        if self._data_format:
            return self._data_format
        if self.dict_data:
            self._data_format = SmarterApiManifDataFormats.JSON
        elif self.yaml_data:
            self._data_format = SmarterApiManifDataFormats.YAML
        return None

    @property
    def data(self) -> dict:
        if self._dict_data:
            return self._dict_data
        if self.data_format == SmarterApiManifDataFormats.JSON:
            self._dict_data = self.dict_data
        elif self.data_format == SmarterApiManifDataFormats.YAML:
            self._dict_data = self.yaml_data
        return self._dict_data

    def get_key(self, key) -> any:
        try:
            return self.data[key]
        except KeyError:
            pass
        return None

    def get_spec(self) -> dict:
        return self._spec

    def validate(self, data: dict = None, spec: dict = None):
        """
        Validate the manifest data. Recursively validate dict keys based on the
        contents of spec.
        """
        spec = spec or self.get_spec()
        data = data or self.data
        if not data:
            raise SmarterApiManifestValidationError("Received empty or invalid data.")

        for key, key_spec in spec.items():
            if isinstance(key_spec, dict):
                value = data.get(key)
                self.validate(value, key_spec)
            else:
                validate_key(key, spec, data)
