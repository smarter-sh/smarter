"""PluginMeta app models."""

from abc import abstractmethod
from typing import Any, Optional, Union

from django.db import models

from smarter.common.exceptions import SmarterValueError
from smarter.lib import json
from smarter.lib.django.models import (
    TimestampedModel,
)

from .plugin_meta import PluginMeta
from .validators import validate_openai_parameters_dict


class PluginDataBase(TimestampedModel):
    """
    Abstract base class for all plugin data configuration models in the Smarter platform.

    ``PluginDataBase`` defines the common interface and fields required for storing and validating
    plugin data specifications, including parameter schemas, test values, and descriptive metadata.
    It is not intended to be instantiated directly, but rather to be subclassed by concrete data
    models such as :class:`PluginDataStatic`, :class:`PluginDataSql`, and :class:`PluginDataApi`,
    each of which implements data handling for a specific plugin type (static, SQL, or API).

    This base class enforces a consistent structure for plugin data models by providing:
      - A reference to the associated :class:`PluginMeta` instance, linking data configuration to plugin metadata.
      - A ``description`` field for documenting the data returned by the plugin.
      - A ``parameters`` field for specifying the expected input schema, validated against OpenAI-compatible conventions.
      - A ``test_values`` field for storing example parameter values used in validation and testing.
      - Abstract methods for returning sanitized data and the plugin's data payload, which must be implemented by subclasses.
      - Validation methods to ensure that all parameters are covered by test values and that test values conform to the expected structure.

    Subclasses are responsible for implementing the logic to return data in the appropriate format for their plugin type,
    as well as any additional validation or preparation steps required for their data source (e.g., SQL query, API request, or static data).

    This class is foundational for the plugin data architecture, ensuring that all plugin data models in the Smarter system
    adhere to a uniform interface and validation strategy.

    See also:

    - :class:`PluginDataStatic`
    - :class:`PluginDataSql`
    - :class:`PluginDataApi`
    - :class:`PluginMeta`
    """

    def __str__(self) -> str:
        plugin: PluginMeta = self.plugin
        user_profile = plugin.user_profile if self.plugin else "No User Profile"
        user_profile = str(user_profile)
        name = str(plugin.name) if plugin else "No Plugin Name"
        return str("<" + user_profile + " - " + name + ">")

    plugin = models.OneToOneField(PluginMeta, on_delete=models.CASCADE, related_name="plugin_data_base_plugin")

    description = models.TextField(
        help_text="A brief description of what this plugin returns. Be verbose, but not too verbose.",
    )
    parameters = models.JSONField(
        help_text="A JSON dict containing parameter names and data types. Example: {'required': [], 'properties': {'max_cost': {'type': 'float', 'description': 'the maximum cost that a student is willing to pay for a course.'}, 'description': {'enum': ['AI', 'mobile', 'web', 'database', 'network', 'neural networks'], 'type': 'string', 'description': 'areas of specialization for courses in the catalogue.'}}}",
        default=dict,
        blank=True,
        null=True,
        validators=[validate_openai_parameters_dict],
        encoder=json.SmarterJSONEncoder,
    )
    """
    A JSON dict containing parameter names and data types.

    Example: {'required': [], 'properties': {'max_cost': {'type': 'float', 'description': 'the maximum cost that a student is willing to pay for a course.'}, 'description': {'enum': ['AI', 'mobile', 'web', 'database', 'network', 'neural networks'], 'type': 'string', 'description': 'areas of specialization for courses in the catalogue.'}}}
    """

    test_values = models.JSONField(
        help_text="A JSON dict containing test values for each parameter. Example: {'city': 'San Francisco'}",
        blank=True,
        null=True,
        encoder=json.SmarterJSONEncoder,
    )
    """
    A JSON dict containing test values for each parameter.

    Example: {'city': 'San Francisco'}
    """

    @abstractmethod
    def sanitized_return_data(self, params: Optional[dict] = None) -> dict:
        """Returns a dict of custom data return results."""
        raise NotImplementedError

    @abstractmethod
    def data(self, params: Optional[dict] = None) -> dict:
        """Returns a dict of custom data return results."""
        raise NotImplementedError

    def validate_all_parameters_in_test_values(self) -> None:
        """
        Ensure that every parameter defined in ``parameters['properties']`` has a corresponding entry in ``test_values``.

        This method checks that all parameter names specified in the ``parameters`` field are present in the ``test_values`` list.
        Each test value should be a dictionary with a ``name`` key matching a parameter name.

        **Example:**

            .. code-block:: python

                parameters = {
                    "properties": {
                        "description": {"type": "string"},
                        "max_cost": {"type": "float"}
                    }
                }
                test_values = [
                    {"name": "description", "value": "AI"},
                    {"name": "max_cost", "value": "500.0"}
                ]

        If any parameter is missing from ``test_values``, a :class:`SmarterValueError` is raised.

        :raises SmarterValueError: If a parameter is defined in ``parameters`` but not present in ``test_values``.
        """
        if self.parameters is None or self.test_values is None:
            return None
        parameters: dict[str, Any] = {}

        try:
            if not isinstance(self.parameters, dict):
                parameters = json.loads(self.parameters)
            else:
                parameters = self.parameters
        except json.JSONDecodeError as e:
            raise SmarterValueError(f"Invalid JSON in parameters. This is a bug: {e}") from e
        if "properties" not in parameters or not isinstance(parameters["properties"], dict):
            raise SmarterValueError(
                "Parameters must be a dict with a 'properties' key containing parameter definitions."
            )
        try:
            if not isinstance(self.test_values, list):
                test_values = json.loads(self.test_values)
            else:
                test_values = self.test_values
        except json.JSONDecodeError as e:
            raise SmarterValueError(f"Invalid JSON in test_values. This is a bug: {e}") from e
        if not isinstance(test_values, list):
            raise SmarterValueError(f"test_values must be a list but got: {type(test_values)}")

        properties = parameters["properties"]

        if isinstance(test_values, list):
            test_values_names = [tv["name"] for tv in test_values if isinstance(tv, dict) and "name" in tv]
            for param_name in properties:
                if param_name not in test_values_names:
                    raise SmarterValueError(
                        f"Parameter '{param_name}' is defined in parameters but not in test_values. "
                        "Ensure all parameters have corresponding test values."
                    )
                if not any(tv["name"] == param_name for tv in test_values):
                    raise SmarterValueError(
                        f"Test value for parameter '{param_name}' is missing. "
                        "Ensure all parameters have corresponding test values."
                    )

    @classmethod
    def get_cached_data_by_plugin(cls, plugin: PluginMeta, invalidate: bool = False) -> Union["PluginDataBase", None]:

        raise NotImplementedError("Subclasses must implement get_cached_data_by_plugin method.")

    def save(self, *args, **kwargs):
        """Override the save method to validate the field dicts."""
        self.validate()
        super().save(*args, **kwargs)
        self.get_cached_data_by_plugin(self.plugin, invalidate=True)
