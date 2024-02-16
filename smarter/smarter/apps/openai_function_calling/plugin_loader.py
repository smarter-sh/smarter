# -*- coding: utf-8 -*-
# pylint: disable=E1101
"""
This module contains the Plugin class, which is used to parse YAML plugin objects for
plugin.function_calling_plugin().
"""
import json
import os
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator, root_validator

from smarter.apps.common.conf import settings
from smarter.apps.common.const import PYTHON_ROOT, VALID_CHAT_COMPLETION_MODELS
from smarter.apps.common.logger import get_logger


log = get_logger(__name__)
CONFIG_PATH = PYTHON_ROOT + "/smarter/apps/openai_function_calling/plugins/"
VALID_PLUGIN_VERSIONS = ["0.1.0"]
VALID_DIRECTIVES = ["search_terms", "always_load"]


def do_error(class_name: str, err: str) -> None:
    """Print the error message and raise a ValueError"""
    err = f"{class_name} - {err}"
    print(err)
    log.error(err)
    raise ValueError(err)


def validate_required_keys(class_name: str, required_keys: list, plugin_json: dict) -> None:
    """Validate the required keys"""
    for key in required_keys:
        if key not in plugin_json:
            do_error(class_name, err=f"Invalid {class_name}: {plugin_json}. Missing key: {key}.")


class PluginBase(BaseModel):
    """Base class for Plugin and Plugins"""

    class Config:
        """Pydantic plugin"""

        extra = "forbid"  # this will forbid any extra attributes during model initialization

    def __repr__(self):
        return f"{self.__class__.__name__}({self.__dict__})"

    def __str__(self):
        return f"{self.to_json()}"

    def to_json(self) -> json:
        """Return the plugin as a JSON object"""
        raise NotImplementedError


class SearchTerms(PluginBase):
    """Search terms of a Plugin object"""

    plugin_json: dict = Field(..., description="Plugin object")

    @field_validator("plugin_json")
    @classmethod
    def validate_plugin_json(cls, plugin_json) -> dict:
        """Validate the plugin_json object"""
        if not isinstance(plugin_json, dict):
            do_error(class_name=cls.__name__, err=f"Expected a dict but received {type(plugin_json)}")

        required_keys = ["search_terms", "pairs"]
        validate_required_keys(class_name=cls.__name__, required_keys=required_keys, plugin_json=plugin_json)

        search_terms = plugin_json["search_terms"]
        pairs = plugin_json["pairs"]
        if not all(isinstance(item, str) for item in search_terms):
            do_error(
                class_name=cls.__name__,
                err=f"Invalid plugin object: {search_terms}. 'search_terms' should be a list of search_terms.",
            )

        if not all(
            isinstance(pair, list) and len(pair) == 2 and all(isinstance(item, str) for item in pair) for pair in pairs
        ):
            do_error(
                class_name=cls.__name__,
                err=f"Invalid plugin object: {plugin_json}. 'pairs' should be a list of pairs of search_terms.",
            )
        return plugin_json

    @property
    def search_terms(self) -> list:
        """Return a list of search terms"""
        return self.plugin_json.get("search_terms")

    @property
    def pairs(self) -> list:
        """Return a list of search terms"""
        return self.plugin_json.get("pairs")

    def to_json(self) -> json:
        """Return the plugin as a JSON object"""
        return self.plugin_json


class AdditionalInformation(PluginBase):
    """Additional information of a Plugin object"""

    plugin_json: dict = Field(..., description="Plugin object")

    @field_validator("plugin_json")
    @classmethod
    def validate_plugin_json(cls, plugin_json) -> dict:
        """Validate the plugin object"""
        if not isinstance(plugin_json, dict):
            do_error(class_name=cls.__name__, err=f"Expected a dict but received {type(plugin_json)}")
        return plugin_json

    @property
    def keys(self) -> list:
        """Return a list of keys for additional information"""
        return list(self.plugin_json.keys())

    def to_json(self) -> json:
        """Return the plugin as a JSON object"""
        return self.plugin_json


class Prompting(PluginBase):
    """Prompting child class of a Plugin object"""

    plugin_json: dict = Field(..., description="Plugin object")

    # attributes
    system_role: str = Field("", description="System prompt of the prompt")
    model: str = Field("gpt-3.5-turbo-1106", description="Model of the system prompt")
    temperature: float = Field(0.0, description="Temperature of the system prompt")
    max_tokens: int = Field(0, description="Max tokens of the system prompt")

    @root_validator(pre=True)
    def set_fields(cls, values):
        """proxy for __init__() - Set the fields"""
        plugin_json = values.get("plugin_json")
        if not isinstance(plugin_json, dict):
            raise ValueError(f"Expected plugin_json to be a dict but received {type(plugin_json)}")
        if plugin_json:
            values["system_role"] = plugin_json["system_role"]
            values["model"] = plugin_json["model"]
            values["temperature"] = plugin_json["temperature"]
            values["max_tokens"] = plugin_json["max_tokens"]
        return values

    @field_validator("plugin_json")
    @classmethod
    def validate_plugin_json(cls, plugin_json) -> dict:
        """Validate the plugin object"""
        required_keys = ["system_role"]
        validate_required_keys(class_name=cls.__name__, required_keys=required_keys, plugin_json=plugin_json)
        return plugin_json

    @field_validator("model")
    @classmethod
    def validate_model(cls, model) -> dict:
        """Validate the plugin object"""
        if model not in VALID_CHAT_COMPLETION_MODELS:
            do_error(
                class_name=cls.__name__,
                err=f"Invalid plugin object: {model}. 'model' should be one of {VALID_CHAT_COMPLETION_MODELS}.",
            )
        return model

    @property
    def system_role(self) -> str:
        """Return the system prompt"""
        return self.plugin_json.get("system_role")

    @property
    def model(self) -> str:
        """Return the model"""
        return self.plugin_json.get("model")

    @property
    def temperature(self) -> float:
        """Return the temperature"""
        return self.plugin_json.get("temperature")

    @property
    def max_tokens(self) -> int:
        """Return the max tokens"""
        return self.plugin_json.get("max_tokens")

    def to_json(self) -> json:
        """Return the plugin as a JSON object"""
        return self.plugin_json


class FunctionCalling(PluginBase):
    """FunctionCalling child class of a Plugin"""

    plugin_json: dict = Field(..., description="Plugin object")
    description: str = Field(None, description="Description of the function")
    return_data: AdditionalInformation = Field(None, description="Additional information of the function")

    @root_validator(pre=True)
    def set_fields(cls, values):
        """proxy for __init__() - Set the fields"""
        plugin_json = values.get("plugin_json")
        if not isinstance(plugin_json, dict):
            raise ValueError(f"Expected plugin_json to be a dict but received {type(plugin_json)}")
        if plugin_json:
            values["description"] = plugin_json["description"]
            values["return_data"] = AdditionalInformation(plugin_json=plugin_json["return_data"])
        return values

    @field_validator("plugin_json")
    @classmethod
    def validate_plugin_json(cls, plugin_json) -> dict:
        """Validate the plugin object"""
        if not isinstance(plugin_json, dict):
            do_error(class_name=cls.__name__, err=f"Expected a dict but received {type(plugin_json)}")
        required_keys = ["description", "return_data"]
        validate_required_keys(class_name=cls.__name__, required_keys=required_keys, plugin_json=plugin_json)
        if not isinstance(plugin_json["description"], str):
            do_error(
                class_name=cls.__name__,
                err=f"Invalid plugin object: {plugin_json}. 'description' should be a string.",
            )
        if not isinstance(plugin_json["return_data"], dict):
            do_error(
                class_name=cls.__name__,
                err=f"Invalid plugin object: {plugin_json}. 'return_data' should be a dict.",
            )
        return plugin_json

    def to_json(self) -> json:
        """Return the plugin as a JSON object"""
        return {
            "description": self.description,
            "return_data": self.return_data.to_json(),
        }


class MetaData(PluginBase):
    """Metadata of a Plugin object"""

    plugin_json: dict = Field(..., description="Plugin object")

    @root_validator(pre=True)
    def set_fields(cls, values):
        """proxy for __init__() - Set the fields"""
        plugin_json = values.get("plugin_json")
        if not isinstance(plugin_json, dict):
            raise ValueError(f"Expected plugin_json to be a dict but received {type(plugin_json)}")
        return values

    @field_validator("plugin_json")
    @classmethod
    def validate_plugin_json(cls, plugin_json) -> dict:
        """Validate the plugin object"""
        if not isinstance(plugin_json, dict):
            do_error(class_name=cls.__name__, err=f"Expected a dict but received {type(plugin_json)}")

        required_keys = ["name", "description", "version", "author"]
        validate_required_keys(class_name=cls.__name__, required_keys=required_keys, plugin_json=plugin_json)
        if str(plugin_json["version"]) not in VALID_PLUGIN_VERSIONS:
            do_error(
                class_name=cls.__name__,
                err=f"Invalid plugin object: {plugin_json}. 'version' should be one of {VALID_PLUGIN_VERSIONS}.",
            )
        return plugin_json

    @property
    def name(self) -> str:
        """Return the name of the plugin object"""
        return self.plugin_json.get("name") if self.plugin_json else None

    @property
    def description(self) -> str:
        """Return the description of the plugin object"""
        return self.plugin_json.get("description") if self.plugin_json else None

    @property
    def version(self) -> str:
        """Return the version of the plugin object"""
        return self.plugin_json.get("version") if self.plugin_json else None

    @property
    def author(self) -> str:
        """Return the author of the plugin object"""
        return self.plugin_json.get("author") if self.plugin_json else None

    def to_json(self) -> json:
        """Return the plugin as a JSON object"""
        return self.plugin_json


class Selector(PluginBase):
    """Selector of a Plugin object"""

    plugin_json: dict = Field(..., description="Plugin object")
    directive: str = Field(None, description="Directive of the Selector object")
    search_terms: SearchTerms = Field(None, description="Search terms of the Selector object")

    @root_validator(pre=True)
    def set_fields(cls, values):
        """proxy for __init__() - Set the fields"""
        plugin_json = values.get("plugin_json")

        if not isinstance(plugin_json, dict):
            raise ValueError(f"Expected plugin_json to be a dict but received {type(plugin_json)}")
        if plugin_json:
            values["directive"] = plugin_json["directive"]
            values["search_terms"] = SearchTerms(plugin_json=plugin_json["search_terms"])
        return values

    @field_validator("plugin_json")
    @classmethod
    def validate_plugin_json(cls, plugin_json) -> dict:
        """Validate the plugin object"""
        required_keys = ["directive", "search_terms"]
        validate_required_keys(class_name=cls.__name__, required_keys=required_keys, plugin_json=plugin_json)
        if not isinstance(plugin_json["directive"], str):
            do_error(
                class_name=cls.__name__,
                err=f"Invalid plugin object: {plugin_json}. 'directive' should be a string.",
            )

    @field_validator("directive")
    @classmethod
    def validate_directive(cls, directive) -> dict:
        """Validate the plugin object"""
        if directive not in VALID_DIRECTIVES:
            do_error(
                class_name=cls.__name__,
                err=f"Invalid plugin object: {directive}. 'directive' should be one of {VALID_DIRECTIVES}.",
            )
        return directive

    def to_json(self) -> json:
        """Return the plugin as a JSON object"""
        return {
            "directive": self.directive,
            "search_terms": self.search_terms.to_json(),
        }


class Plugin(PluginBase):
    """A json object that contains the plugin for a plugin.function_calling_plugin() function"""

    index: int = Field(0, description="Index of the plugin object")
    plugin_json: dict = Field(..., description="Plugin object")

    # Child classes
    meta_data: Optional[MetaData] = Field(None, description="Metadata of the plugin object")
    selector: Optional[Selector] = Field(None, description="Selector of the plugin object")
    prompting: Optional[Prompting] = Field(None, description="Prompting of the plugin object")
    plugin_data: Optional[FunctionCalling] = Field(None, description="FunctionCalling of the plugin object")

    @property
    def name(self) -> str:
        """Return a name in the format: "WillyWonka"""
        return self.meta_data.name

    @root_validator(pre=True)
    def set_fields(cls, values):
        """proxy for __init__() - Set the fields"""
        plugin_json = values.get("plugin_json")
        if not isinstance(plugin_json, dict):
            raise ValueError(f"Expected plugin_json to be a dict but received {type(plugin_json)}")
        if plugin_json:
            values["meta_data"] = MetaData(plugin_json=plugin_json.get("meta_data"))
            values["selector"] = Selector(plugin_json=plugin_json.get("selector"))
            values["prompting"] = Prompting(plugin_json=plugin_json.get("prompting"))
            values["plugin_data"] = FunctionCalling(plugin_json=plugin_json.get("plugin_data"))
        return values

    @field_validator("plugin_json")
    @classmethod
    def validate_plugin_json(cls, plugin_json) -> None:
        """Validate the plugin object"""

        required_keys = ["meta_data", "selector", "prompting", "plugin_data"]
        for key in required_keys:
            if key not in plugin_json:
                cls.do_error(f"Invalid plugin object: {plugin_json}. Missing key: {key}.")
            if not isinstance(plugin_json[key], dict):
                do_error(
                    class_name=cls.__name__,
                    err=f"Expected a dict for {key} but received {type(plugin_json[key])}: {plugin_json[key]}",
                )

    def to_json(self) -> json:
        """Return the plugin as a JSON object"""
        return {
            "name": self.name,
            "meta_data": self.meta_data.to_json(),
            "selector": self.selector.to_json(),
            "prompting": self.prompting.to_json(),
            "plugin_data": self.plugin_data.to_json(),
        }


class Plugins:
    """List of Plugin objects"""

    _custom_plugins: list[Plugin] = None
    _aws_bucket_name: str = None
    _aws_bucket_path: str = "smarter/openai_function_calling/plugins/"
    _aws_bucket_path_validated: bool = False

    def __init__(self, plugin_path: str = None, aws_s3_bucket_name: str = None):
        i = 0
        self._custom_plugins = []
        self._aws_bucket_name = aws_s3_bucket_name
        self.verify_bucket(bucket_name=aws_s3_bucket_name)

        # Load all the plugin objects in this repo
        for filename in os.listdir(plugin_path):
            if filename.endswith((".yaml", ".yml")):
                i += 1
                full_plugin_path = os.path.join(plugin_path, filename)
                with open(full_plugin_path, "r", encoding="utf-8") as file:
                    plugin_json = yaml.safe_load(file)

                plugin = Plugin(plugin_json=plugin_json, index=i)
                self._custom_plugins.append(plugin)

        # Load plugin objects from the AWS S3 bucket
        if self.aws_bucket_path_validated:
            s3 = settings.aws_session.resource("s3")
            bucket = s3.Bucket(self._aws_bucket_name)

            for obj in bucket.objects.filter(Prefix=self.aws_bucket_path):
                if obj.key.endswith(".yaml") or obj.key.endswith(".yml"):
                    i += 1
                    file_content = obj.get()["Body"].read().decode("utf-8")
                    plugin_json = yaml.safe_load(file_content)
                    if plugin_json:
                        plugin = Plugin(plugin_json=plugin_json, index=i)
                        self._custom_plugins.append(plugin)
                        print(
                            f"Loaded plugin from AWS S3 bucket: {plugin.name} {plugin.meta_data.version} created by {plugin.meta_data.author}"
                        )

    @property
    def valid_plugins(self) -> list[Plugin]:
        """Return a list of valid plugins"""
        return self._custom_plugins

    @property
    def invalid_plugins(self) -> list[Plugin]:
        """Return a list of invalid plugins"""
        return []

    @property
    def aws_bucket_path(self) -> str:
        """Return the remote host"""
        return self._aws_bucket_path

    @property
    def aws_bucket_path_validated(self) -> bool:
        """Return True if the remote host is valid"""
        return self._aws_bucket_path_validated

    def verify_bucket(self, bucket_name: str):
        """Verify that the remote host is valid"""
        # If the bucket name is the default, then skip the validation
        if settings.root_domain == "example.com":
            return

        if not bucket_name:
            return

        s3 = settings.aws_session.resource("s3")
        try:
            # Check if bucket exists
            s3.meta.client.head_bucket(Bucket=bucket_name)
        # pylint: disable=broad-exception-caught
        except Exception as e:
            log.warning("Bucket %s does not exist: %s", bucket_name, e)
            return

        # Create any missing folders
        bucket = s3.Bucket(bucket_name)
        if not any(s3_object.key.startswith(self.aws_bucket_path) for s3_object in bucket.objects.all()):
            print(f"Creating folder {self.aws_bucket_path} in bucket {bucket_name}")
            s3.Object(bucket_name, self.aws_bucket_path).put()
        self._aws_bucket_path_validated = True

    def to_json(self) -> json:
        """Return the _custom_plugins list as a JSON object"""
        return self.valid_plugins


class SingletonPlugins:
    """Singleton for Settings"""

    _instance = None
    _custom_plugins = None

    def __new__(cls):
        """Create a new instance of Settings"""
        if cls._instance is None:
            cls._instance = super(SingletonPlugins, cls).__new__(cls)
            cls._instance._custom_plugins = Plugins(
                plugin_path=CONFIG_PATH, aws_s3_bucket_name=settings.aws_s3_bucket_name
            )
        return cls._instance

    @property
    def plugins(self) -> Plugins:
        """Return the settings"""
        return self._custom_plugins


plugins = SingletonPlugins().plugins.valid_plugins
