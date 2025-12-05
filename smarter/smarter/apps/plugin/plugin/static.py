"""A PLugin that returns a static json object stored in the Plugin itself."""

import logging
from typing import Any, Optional, Type

from smarter.apps.plugin.manifest.enum import (
    SAMPluginCommonMetadataClass,
    SAMPluginCommonMetadataClassValues,
    SAMPluginCommonMetadataKeys,
    SAMPluginCommonSpecPromptKeys,
    SAMPluginCommonSpecSelectorKeys,
    SAMPluginSpecKeys,
    SAMStaticPluginSpecDataKeys,
)
from smarter.apps.plugin.models import PluginDataStatic
from smarter.apps.plugin.serializers import PluginStaticSerializer
from smarter.common.api import SmarterApiVersions
from smarter.common.conf import SettingsDefaults
from smarter.common.conf import settings as smarter_settings
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys

from ..manifest.enum import SAMPluginCommonSpecSelectorKeyDirectiveValues
from ..manifest.models.static_plugin.const import MANIFEST_KIND
from ..manifest.models.static_plugin.model import SAMStaticPlugin
from ..signals import plugin_called, plugin_responded
from .base import PluginBase, SmarterPluginError


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class StaticPlugin(PluginBase):
    """
    Implements a plugin that returns a static JSON object stored within the plugin itself.

    This class is intended for use cases where plugin data is immutable at runtime and fully defined in the manifest or configuration. The static data is exposed via the plugin interface and can be accessed through function calls, including those compatible with OpenAI's function calling API.

    Typical uses include providing product details, company contact information, sales promotions, coupon codes, or biographical background. The plugin supports both manifest-based and Django ORM-based initialization for flexible integration.

    **Key Features:**

        - Returns static data defined in the plugin manifest or configuration.
        - Integrates with Django ORM for plugin data persistence.
        - Provides a tool definition compatible with OpenAI function calling.
        - Handles serialization and validation of static data.
        - Emits signals when the plugin is called and when it responds.

    :param manifest: Optional manifest object for plugin initialization.
    :type manifest: Optional[SAMStaticPlugin]
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Additional keyword arguments.
    :type kwargs: dict

    .. note::

        Signals are emitted on plugin call and response for observability and integration.

    .. seealso::

        :class:`PluginBase`
        :class:`PluginDataStatic`
        :class:`PluginStaticSerializer`
        `OpenAI Function Calling Quickstart <https://platform.openai.com/docs/assistants/tools/function-calling/quickstart>`_

    **Example Use Cases:**

        - Providing static product information for a chatbot.
        - Supplying company contact details or promotional codes.
        - Returning biographical information about a company founder.

    """

    SAMPluginType = SAMStaticPlugin

    _manifest: Optional[SAMStaticPlugin] = None
    _metadata_class: str = SAMPluginCommonMetadataClass.STATIC.value
    _plugin_data: Optional[PluginDataStatic] = None
    _plugin_data_serializer: Optional[PluginStaticSerializer] = None

    def __init__(
        self,
        *args,
        manifest: Optional[SAMStaticPlugin] = None,
        **kwargs,
    ):
        super().__init__(*args, manifest=manifest, **kwargs)

    @property
    def manifest(self) -> Optional[SAMStaticPlugin]:
        """
        Return the Pydantic model representation of the plugin manifest.

        This property provides access to the plugin's manifest as a validated Pydantic model
        (:class:`SAMStaticPlugin`). If the manifest has not been set but the plugin is in a ready state,
        it will attempt to construct the manifest from the current plugin data using the ``to_json()`` method.

        Returns
        -------
        Optional[SAMStaticPlugin]
            The Pydantic model instance representing the plugin manifest, or ``None`` if unavailable.

        Notes
        -----
        This property is useful for accessing structured, validated manifest data regardless of whether
        the plugin was initialized from a manifest or from Django ORM data.
        """
        if not self._manifest and self.ready:
            # if we don't have a manifest but we do have Django ORM data then
            # we can work backwards to the Pydantic model
            self._manifest = SAMStaticPlugin(**self.to_json())  # type: ignore[call-arg]
        return self._manifest

    @property
    def plugin_data(self) -> Optional[PluginDataStatic]:
        """
        Return the plugin data as a Django ORM instance.

        This property provides access to the plugin's data as a Django ORM model instance
        (:class:`PluginDataStatic`). The returned object represents the persistent state of the plugin's
        static data in the database.

        The property handles several scenarios:

        - If the plugin was initialized from a manifest and is associated with a database record,
          it will construct the ORM instance from the manifest data.
        - If the plugin is already present in the database but not initialized from a manifest,
          it retrieves the existing ORM instance directly.
        - If neither a manifest nor a database record exists, it returns ``None``.

        This property is useful for interacting with the plugin's data using Django's ORM features,
        such as querying, updating, or serializing the static data.

        Returns
        -------
        Optional[PluginDataStatic]
            The Django ORM instance representing the plugin's static data, or ``None`` if unavailable.

        Notes
        -----
        This property abstracts the logic for resolving the plugin's data source, ensuring that
        consumers of the property always receive a consistent ORM object when possible.
        """
        if self._plugin_data:
            return self._plugin_data
        # we only want a preexisting manifest ostensibly sourced
        # from the cli, not a lazy-loaded
        if self._manifest and self.plugin_meta:
            # this is an update scenario. the Plugin exists in the database,
            # AND we've received manifest data from the cli.
            self._plugin_data = (
                PluginDataStatic(**self.plugin_data_django_model) if self.plugin_data_django_model else None
            )
        if self.plugin_meta:
            # we don't have a Pydantic model but we do have an existing
            # Django ORM model instance, so we can use that directly.
            self._plugin_data = PluginDataStatic.objects.get(
                plugin=self.plugin_meta,
            )
        # new Plugin scenario. there's nothing in the database yet.
        return self._plugin_data

    @property
    def plugin_data_class(self) -> Type[PluginDataStatic]:
        """
        Return the Django ORM class used for static plugin data.

        This property provides the class object for the Django model that represents
        the persistent storage of static plugin data. It is useful for introspection,
        type checking, and for scenarios where you need to interact with the model class
        directly (such as creating new instances, performing queries, or using Django's
        ORM features programmatically).

        The returned class is typically :class:`PluginDataStatic`, which defines the schema
        for storing static data associated with this plugin type.

        :return: The Django ORM class for static plugin data.
        :rtype: Type[PluginDataStatic]
        """
        return PluginDataStatic

    @property
    def plugin_data_serializer(self) -> Optional[PluginStaticSerializer]:
        """
        Return the serializer instance for the plugin's static data.

        This property provides a serializer object (:class:`PluginStaticSerializer`) that is
        initialized with the current plugin data. The serializer is responsible for converting
        the Django ORM model instance to and from native Python datatypes, as well as validating
        and serializing the static data for use in APIs or other interfaces.

        If the serializer has not yet been created, it will be instantiated using the current
        plugin data. This ensures that the serializer always reflects the latest state of the
        plugin's static data.

        :return: The serializer instance for the plugin's static data, or ``None`` if the plugin data is unavailable.
        :rtype: Optional[PluginStaticSerializer]

        Notes
        -----
        The serializer is useful for tasks such as rendering the plugin data as JSON, validating
        incoming data, or preparing the data for use in API responses.
        """
        if not self._plugin_data_serializer:
            self._plugin_data_serializer = PluginStaticSerializer(self.plugin_data)
        return self._plugin_data_serializer

    @property
    def plugin_data_serializer_class(self) -> Type[PluginStaticSerializer]:
        """
        Return the plugin data serializer class.

        This property provides direct access to the serializer class used for static plugin data.
        The serializer class is responsible for converting Django ORM model instances to and from
        native Python datatypes, as well as validating and serializing the static data for use in
        APIs or other interfaces.

        Accessing the serializer class is useful when you need to instantiate a new serializer,
        perform type checks, or customize serialization behavior for static plugin data.

        :return: The serializer class for static plugin data.
        :rtype: Type[PluginStaticSerializer]

        Notes
        -----
        This property does not return an instance, but rather the class itself, allowing for
        flexible instantiation and extension in advanced use cases.
        """
        return PluginStaticSerializer

    @property
    def plugin_data_django_model(self) -> Optional[dict[str, Any]]:
        """
        Transform the Pydantic model into a Django ORM-compatible dictionary.

        This property generates a dictionary representation of the plugin's static data,
        suitable for initializing or updating a Django ORM model instance (:class:`PluginDataStatic`).
        The dictionary includes all fields required by the ORM model, such as the plugin reference,
        description, and static data payload.

        The transformation is performed using the current Pydantic manifest model, if available.
        This allows for seamless conversion between validated manifest data and the persistent
        database representation used by Django.

        Returns
        -------
        Optional[dict[str, Any]]
            A dictionary containing the fields necessary to create or update a
            :class:`PluginDataStatic` ORM instance, or ``None`` if the manifest is not available.

        Notes
        -----
        This property is useful for bridging the gap between Pydantic-based manifest validation
        and Django ORM persistence, enabling consistent data handling across both systems.
        """
        # recast the Pydantic model the the PluginDataStatic Django ORM model
        if self._manifest:
            return {
                "plugin": self.plugin_meta,
                "description": (
                    self.manifest.spec.data.description
                    if self.manifest and self.manifest.spec and self.manifest.spec.data
                    else None
                ),
                "static_data": (
                    self.manifest.spec.data.staticData
                    if self.manifest and self.manifest.spec and self.manifest.spec.data
                    else None
                ),
            }

    @property
    def custom_tool(self) -> Optional[dict[str, Any]]:
        """
        Return the plugin tool definition for OpenAI function calling.

        See the OpenAI documentation:
        https://platform.openai.com/docs/assistants/tools/function-calling/quickstart

        **Example:**

        .. code-block:: python

            tool = {
                "type": "function",
                "function": {
                    "name": "static_plugin_function",
                    "description": "Static Plugin",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "inquiry_type": {
                                "type": "string",
                                "enum": ["contact", "biographical", "sales_promotions", "coupon_codes"],
                            },
                        },
                        "required": ["inquiry_type"],
                    },
                },
            }
        """
        if self.ready:
            return {
                "type": "function",
                "function": {
                    "name": self.function_calling_identifier,
                    "description": self.plugin_data.description if self.plugin_data else "Static Plugin",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "inquiry_type": {
                                "type": "string",
                                "enum": self.plugin_data.return_data_keys if self.plugin_data else None,
                            },
                        },
                        "required": ["inquiry_type"],
                    },
                },
            }
        return None

    @classmethod
    def example_manifest(cls, kwargs: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
        """
        Return an example manifest for a StaticPlugin.

        :param kwargs: Optional keyword arguments to customize the example manifest.
        :type kwargs: Optional[dict[str, Any]]

        :return: An example manifest as a dictionary.
        :rtype: Optional[dict[str, Any]]

        :raises SmarterConfigurationError: If there is an error generating the example manifest.

        See Also:

        - :class:`SAMStaticPlugin`
        - :class:`SmarterApiVersions`
        - :class:`SAMKeys`
        - :class:`SAMMetadataKeys`
        - :class:`SAMPluginCommonMetadataKeys`
        - :class:`SAMPluginCommonMetadataClassValues`
        - :class:`SAMPluginSpecKeys`
        - :class:`SAMPluginCommonSpecSelectorKeys`
        - :class:`SAMPluginCommonSpecSelectorKeyDirectiveValues`
        - :class:`SAMPluginCommonSpecPromptKeys`
        - :class:`SAMStaticPluginSpecDataKeys`

        """
        static_plugin = {
            SAMKeys.APIVERSION.value: SmarterApiVersions.V1,
            SAMKeys.KIND.value: MANIFEST_KIND,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "everlasting_gobstopper",
                SAMPluginCommonMetadataKeys.PLUGIN_CLASS.value: SAMPluginCommonMetadataClassValues.STATIC.value,
                SAMMetadataKeys.DESCRIPTION.value: "Get additional information about the Everlasting Gobstopper product created by Willy Wonka Chocolate Factory. Information includes sales promotions, coupon codes, company contact information and biographical background on the company founder.",
                SAMMetadataKeys.VERSION.value: "0.1.0",
                SAMMetadataKeys.TAGS.value: ["candy", "treats", "chocolate", "Gobstoppers", "Willy Wonka"],
            },
            SAMKeys.SPEC.value: {
                SAMPluginSpecKeys.SELECTOR.value: {
                    SAMPluginCommonSpecSelectorKeys.DIRECTIVE.value: SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value,
                    SAMPluginCommonSpecSelectorKeys.SEARCHTERMS.value: [
                        "Gobstopper",
                        "Gobstoppers",
                        "Gobbstopper",
                        "Gobbstoppers",
                    ],
                },
                SAMPluginSpecKeys.PROMPT.value: {
                    SAMPluginCommonSpecPromptKeys.PROVIDER.value: SettingsDefaults.LLM_DEFAULT_PROVIDER,
                    SAMPluginCommonSpecPromptKeys.SYSTEMROLE.value: "You are a helpful marketing agent for the [Willy Wonka Chocolate Factory](https://wwcf.com). Whenever possible you should defer to the tool calls provided for additional information about everlasting gobstoppers.",
                    SAMPluginCommonSpecPromptKeys.MODEL.value: SettingsDefaults.LLM_DEFAULT_MODEL,
                    SAMPluginCommonSpecPromptKeys.TEMPERATURE.value: SettingsDefaults.LLM_DEFAULT_TEMPERATURE,
                    SAMPluginCommonSpecPromptKeys.MAXTOKENS.value: SettingsDefaults.LLM_DEFAULT_MAX_TOKENS,
                },
                SAMPluginSpecKeys.DATA.value: {
                    SAMStaticPluginSpecDataKeys.DESCRIPTION.value: "Get additional information about the Everlasting Gobstopper product created by Willy Wonka Chocolate Factory. Information includes sales promotions, coupon codes, company contact information and biographical background on the company founder.",
                    SAMStaticPluginSpecDataKeys.STATIC.value: {
                        "contact": [
                            {"name": "Willy Wonka"},
                            {"title": "Founder and CEO"},
                            {"location": "1234 Chocolate Factory Way, Chocolate City, Chocolate State, USA"},
                            {"phone": "+1 123-456-7890"},
                            {"website_url": "https://wwcf.com"},
                            {"whatsapp": 11234567890},
                            {"email": "ww@wwcf.com"},
                        ],
                        "biographical": "Willy Wonka is a fictional character appearing in British author Roald Dahl's 1964 children's novel Charlie and the Chocolate Factory, its 1972 sequel Charlie and the Great Glass Elevator and several films based on those books. He is the eccentric founder and proprietor of the Wonka Chocolate Factory\n",
                        "sales_promotions": [
                            {
                                "name": "Everlasting Gobstopper",
                                "description": 'The Everlasting Gobstopper is a candy that, according to Willy Wonka, "Never Gets Smaller Or Ever Gets Eaten". It is the main focus of Charlie and the Chocolate Factory, both the 1971 film and the 2005 film, and Willy Wonka and the Chocolate Factory, the 1971 film adaptation of the novel.\n',
                                "price": "$1.00",
                                "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/Everlasting_Gobstopper.jpg/220px-Everlasting_Gobstopper.jpg",
                            },
                            {
                                "name": "Wonka Bar",
                                "description": "Wonka Bars are a fictional brand of chocolate made by Willy Wonka, and also a chocolate bar inspired by the Willy Wonka Bar from the novel and the films Willy Wonka & the Chocolate Factory and Charlie and the Chocolate Factory.\n",
                                "price": "$1.00",
                                "image": "https://m.media-amazon.com/images/I/81E-734cMzL._AC_UF894,1000_QL80_.jpg",
                            },
                        ],
                        "coupon_codes": [
                            {"name": "10% off", "code": "10OFF", "description": "10% off your next purchase\n"},
                            {"name": "20% off", "code": "20OFF", "description": "20% off your next purchase\n"},
                        ],
                    },
                },
            },
        }

        # recast the Python dict to the Pydantic model
        # in order to validate our output
        pydantic_model = cls.SAMPluginType(**static_plugin)
        return json.loads(pydantic_model.model_dump_json())

    def tool_call_fetch_plugin_response(self, function_args: dict[str, Any]) -> str:
        """
        Fetch a response from the StaticPlugin based on the provided inquiry type.

        This method retrieves the value associated with the specified ``inquiry_type`` from the plugin's static data.
        It is intended for use with function calling interfaces, such as those provided by OpenAI, where the inquiry
        type is passed as an argument and the corresponding static data is returned as a JSON-encoded string.

        The method performs several validation steps:

        - Ensures that the ``inquiry_type`` argument is present and is a string.
        - Verifies that the plugin is in a ready state and that plugin data is available.
        - Emits signals when the plugin is called and when it responds.
        - Looks up the value for the given inquiry type in the plugin's static data.
        - Serializes the result to a JSON string before returning.
        - Raises detailed errors if any step fails, including missing inquiry types, serialization issues, or invalid data.

        Parameters
        ----------
        function_args : dict[str, Any]
            A dictionary of arguments, expected to include the key ``inquiry_type`` specifying which static data to fetch.

        Returns
        -------
        str
            The JSON-encoded string corresponding to the requested inquiry type.

        Raises
        ------
        SmarterPluginError
            If the inquiry type is missing, not a string, not found in the static data, or if the plugin is not ready or lacks data.
            Also raised if the return value cannot be serialized to JSON or is not a string.

        Notes
        -----
        This method is typically used as the handler for function calling APIs, enabling external systems to retrieve
        specific pieces of static information from the plugin in a robust and validated manner.
        """
        inquiry_type = function_args.get("inquiry_type")
        if not isinstance(inquiry_type, str):
            raise SmarterPluginError(
                f"Plugin {self.name} invalid inquiry_type. Expected a string, got {type(inquiry_type)}.",
            )

        if not self.ready:
            raise SmarterPluginError(
                f"Plugin {self.name} is not in a ready state.",
            )

        if not self.plugin_data:
            raise SmarterPluginError(
                f"Plugin {self.name} is not ready. Plugin data is not available.",
            )

        plugin_called.send(
            sender=self.tool_call_fetch_plugin_response,
            plugin=self,
            inquiry_type=inquiry_type,
        )

        try:
            return_data = self.plugin_data.sanitized_return_data(self.params)
            if not isinstance(return_data, dict):
                raise SmarterPluginError(
                    f"Plugin {self.name} return data is not a dictionary.",
                )

            try:
                retval = return_data[inquiry_type]
            except KeyError as e:
                raise SmarterPluginError(
                    f"Plugin {self.name} does not have a return value for inquiry_type: {inquiry_type}. Available keys are: {list(return_data.keys())} from return_data {json.dumps(return_data)}.",
                ) from e

            if retval is None:
                raise SmarterPluginError(
                    f"Plugin {self.name} return value for inquiry_type: {inquiry_type} is None.",
                )

            try:
                retval = json.dumps(retval)
            except (TypeError, ValueError) as e:
                raise SmarterPluginError(
                    f"Plugin {self.name} return value for inquiry_type: {inquiry_type} could not be serialized to JSON: {e}.",
                ) from e

            if not isinstance(retval, str):
                raise SmarterPluginError(
                    f"Plugin {self.name} return value for inquiry_type: {inquiry_type} is not a string. Expected a string, got {type(retval)}.",
                )
            plugin_responded.send(
                sender=self.tool_call_fetch_plugin_response,
                plugin=self,
                inquiry_type=inquiry_type,
                response=retval,
            )
            return retval
        except KeyError as e:
            raise SmarterPluginError(
                f"Plugin {self.name} does not have a return value for inquiry_type: {inquiry_type}.",
            ) from e
        except json.JSONDecodeError as e:
            raise SmarterPluginError(
                f"Plugin {self.name} contains Json data that could not be decoded: {e}.",
            ) from e
