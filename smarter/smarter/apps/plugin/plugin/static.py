"""
A Plugin that returns static data stored in the Plugin itself.

.. note::

    This is a complex AI resource that exists within the following class hierarchy

    1. Smarter Static Plugin: The plugin that defines the static data, organized by inquiry type, that it returns to the LLM.
    2. Smarter LLMClient: The prompting resource (LLMClient, Agent, Workflow unit, etcetera) that includes the Static Plugin.

.. note::

    The structure of ``spec.data.staticData`` has semantic meaning. Its keys are the
    *inquiry types* that the LLM can request, and each key's value is the data returned
    for that inquiry type. Keys of nested dicts are inquiry types too. In the example
    manifest below, the LLM can request ``contact``, ``biographical``,
    ``salesPromotions`` or ``couponCodes``.

.. sphinx note: these are relative to the rst doc that calls automodule on this file.

.. literalinclude:: ../../../../../smarter/smarter/apps/plugin/data/sample-plugins/everlasting-gobstopper.yaml
    :language: yaml
    :caption: 1.) Example Static Plugin Manifest

.. literalinclude:: ../../../../../smarter/smarter/apps/llmclient/data/llm-clients/llmclient-example.yaml
    :language: yaml
    :caption: 2.) Example LLMClient Manifest
"""

from datetime import datetime
from typing import Any, Optional, Type, Union

from smarter.apps.plugin.manifest.enum import (
    SAMPluginCommonMetadataClass,
    SAMPluginCommonMetadataClassValues,
    SAMPluginCommonSpecSelectorKeyDirectiveValues,
)
from smarter.apps.plugin.manifest.models.common.plugin.metadata import (
    SAMPluginCommonMetadata,
)
from smarter.apps.plugin.manifest.models.common.plugin.spec import (
    SAMPluginCommonSpecPrompt,
    SAMPluginCommonSpecSelector,
)
from smarter.apps.plugin.manifest.models.common.plugin.status import (
    SAMPluginCommonStatus,
)
from smarter.apps.plugin.manifest.models.static_plugin.const import MANIFEST_KIND
from smarter.apps.plugin.manifest.models.static_plugin.model import SAMStaticPlugin
from smarter.apps.plugin.manifest.models.static_plugin.spec import (
    SAMPluginStaticSpec,
    SAMPluginStaticSpecData,
)
from smarter.apps.plugin.models import PluginDataStatic
from smarter.apps.plugin.serializers import PluginStaticSerializer
from smarter.apps.plugin.signals import plugin_called, plugin_responded
from smarter.common.api import SmarterApiVersions
from smarter.common.conf import settings_defaults
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json, logging
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .base import PluginBase, SmarterPluginError


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)


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

        - Providing static product information for an llmclient.
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

        if not self.plugin_meta:
            # new Plugin scenario, or a plugin that is not ready. there's nothing in the database yet.
            return None

        try:
            self._plugin_data = PluginDataStatic.get_cached_object(plugin=self.plugin_meta)  # type: ignore[call-arg]
            logger.debug(
                "%s.plugin_data() retrieved existing PluginDataStatic from database.",
                self.formatted_class_name,
            )
            return self._plugin_data
        except PluginDataStatic.DoesNotExist:
            logger.debug(
                "%s.plugin_data() no existing PluginDataStatic found in database for plugin_meta: %s",
                self.formatted_class_name,
                self.plugin_meta,
            )

        # we only want a preexisting manifest ostensibly sourced
        # from the cli, not a lazy-loaded
        if self._manifest and self.plugin_meta:
            # this is an update scenario. the Plugin exists in the database,
            # AND we've received manifest data from the cli.
            self._plugin_data = PluginDataStatic(**self.plugin_data_django_model)  # type: ignore[call-arg]
            self._plugin_data.save()
            logger.debug(
                "%s.plugin_data() created new instance of %s from manifest and plugin metadata.",
                self.formatted_class_name,
                self.plugin_data_class.__name__,
            )
        if self.plugin_meta:
            # we don't have a Pydantic model but we do have an existing
            # Django ORM model instance, so we can use that directly.
            logger.debug(
                "%s.plugin_data() retrieving PluginDataStatic from database using plugin metadata.",
                self.formatted_class_name,
            )
            self._plugin_data = PluginDataStatic.get_cached_data_by_plugin(
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
        # recast the Pydantic model to the PluginDataStatic Django ORM model
        if not self._manifest:
            return None
        return {
            "plugin": self.plugin_meta,
            # the description is presented to the LLM as the tool description. it is
            # metadata.description of the manifest. spec.data.description would be redundant.
            "description": (
                self._manifest.metadata.description
                if self._manifest.metadata and self._manifest.metadata.description
                else self.plugin_meta.description if self.plugin_meta else ""
            ),
            "static_data": (
                self._manifest.spec.data.staticData if self._manifest.spec and self._manifest.spec.data else None
            ),
        }

    @property
    def inquiry_types(self) -> list[str]:
        """
        Return the inquiry types that the LLM can request from this plugin.

        The inquiry types are the keys of ``staticData``, including the keys of nested dicts,
        without duplicates. Keys inside lists are not inquiry types. Their order is the order
        in which the database returns the static data. They are presented to the LLM as the
        ``enum`` of the ``inquiry_type`` function parameter, and each one can be resolved by
        :meth:`tool_call_fetch_plugin_response`.

        :return: The inquiry types, or an empty list if the plugin data is not available.
        :rtype: list[str]

        **Example:**

        .. code-block:: yaml

            staticData:
              contact:
                - name: Willy Wonka
              biographical: >
                Willy Wonka is a fictional character ...
              hours:
                weekdays: 9am - 5pm
                weekends: closed

        .. code-block:: python

            plugin.inquiry_types
            # ['contact', 'biographical', 'hours', 'weekdays', 'weekends']
        """
        keys = self.plugin_data.return_data_keys if self.plugin_data else None
        return list(dict.fromkeys(str(key) for key in keys or []))

    @property
    def custom_tool(self) -> Optional[dict[str, Any]]:  # type: ignore[override]
        """
        Return the plugin tool definition for OpenAI function calling.

        The tool takes a single required parameter, ``inquiry_type``, whose ``enum`` is
        :attr:`inquiry_types`. The ``enum`` is omitted if the plugin has no inquiry types,
        since a null ``enum`` is not a valid JSON schema.

        See the OpenAI documentation:
        https://platform.openai.com/docs/assistants/tools/function-calling/quickstart

        :return: The tool definition, or ``None`` if the plugin is not ready.
        :rtype: Optional[dict[str, Any]]

        **Example:**

        .. code-block:: python

            tool = {
                "type": "function",
                "function": {
                    "name": "smarter_plugin_0000000042",
                    "description": "Get additional information about the Everlasting Gobstopper ...",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "inquiry_type": {
                                "type": "string",
                                "enum": ["contact", "biographical", "salesPromotions", "couponCodes"],
                            },
                        },
                        "required": ["inquiry_type"],
                    },
                },
            }
        """
        if not self.ready:
            return None
        description = (
            (self.plugin_data.description if self.plugin_data else None)
            or (self.plugin_meta.description if self.plugin_meta else None)
            or "Static Plugin"
        )
        inquiry_type: dict[str, Any] = {"type": "string"}
        if self.inquiry_types:
            inquiry_type["enum"] = self.inquiry_types
        return {
            "type": "function",
            "function": {
                "name": self.function_calling_identifier,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": {"inquiry_type": inquiry_type},
                    "required": ["inquiry_type"],
                },
            },
        }

    @classmethod
    def example_manifest(cls, kwargs: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
        """
        Use Pydantic models to generate an example manifest for a StaticPlugin.

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
        metadata = SAMPluginCommonMetadata(
            name="everlasting_gobstopper",
            description="Get additional information about the Everlasting Gobstopper product created by Willy Wonka Chocolate Factory. Information includes sales promotions, coupon codes, company contact information and biographical background on the company founder.",
            version="0.1.0",
            tags=["candy", "treats", "chocolate", "Gobstoppers", "Willy Wonka"],
            annotations=[
                {"smarter.sh/created_by": "smarter_static_plugin_broker"},
                {"smarter.sh/plugin": "everlasting_gobstopper"},
            ],
            pluginClass=SAMPluginCommonMetadataClassValues.STATIC.value,
        )
        selector = SAMPluginCommonSpecSelector(
            directive=SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value,
            searchTerms=[
                "Gobstopper",
                "Gobstoppers",
                "Gobbstopper",
                "Gobbstoppers",
            ],
        )
        prompt = SAMPluginCommonSpecPrompt(
            provider=settings_defaults.LLM_DEFAULT_PROVIDER,
            systemRole="You are a helpful marketing agent for the [Willy Wonka Chocolate Factory](https://wwcf.com). Whenever possible you should defer to the tool calls provided for additional information about everlasting gobstoppers.",
            model=settings_defaults.LLM_DEFAULT_MODEL,
            temperature=settings_defaults.LLM_DEFAULT_TEMPERATURE,
            maxTokens=settings_defaults.LLM_DEFAULT_MAX_TOKENS,
        )
        data = SAMPluginStaticSpecData(
            staticData={
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
        )
        spec = SAMPluginStaticSpec(
            selector=selector,
            prompt=prompt,
            data=data,
        )
        status = SAMPluginCommonStatus(
            accountNumber="1234567890",
            username="example_user",
            recordLocator="abc123def456",
            created=datetime(2024, 1, 1, 0, 0, 0),
            modified=datetime(2024, 1, 1, 0, 0, 0),
        )

        sam_static_plugin = SAMStaticPlugin(
            apiVersion=SmarterApiVersions.V1,
            kind=MANIFEST_KIND,
            metadata=metadata,
            spec=spec,
            status=status,
        )

        return json.loads(sam_static_plugin.model_dump_json())

    @classmethod
    def find_inquiry_value(cls, data: dict[str, Any], inquiry_type: str) -> tuple[bool, Any]:
        """
        Find the value of an inquiry type in the static data.

        Keys at the current level take precedence, after which nested dicts are searched
        depth-first. This mirrors how :attr:`inquiry_types` are collected, so that every
        advertised inquiry type can be resolved.

        :param data: The static data.
        :type data: dict[str, Any]
        :param inquiry_type: The inquiry type to find.
        :type inquiry_type: str
        :return: A tuple of (found, value). ``found`` distinguishes a missing inquiry type from one whose value is ``None``.
        :rtype: tuple[bool, Any]

        **Example:**

        .. code-block:: python

            StaticPlugin.find_inquiry_value({"hours": {"weekdays": "9am - 5pm"}}, "weekdays")
            # (True, '9am - 5pm')
        """
        if inquiry_type in data:
            return True, data[inquiry_type]
        for value in data.values():
            if isinstance(value, dict):
                found, nested_value = cls.find_inquiry_value(value, inquiry_type)
                if found:
                    return True, nested_value
        return False, None

    @classmethod
    def to_tool_response(cls, value: Any) -> Union[dict, list, str]:
        """
        Convert a static data value to a tool call response.

        - dicts and lists are returned as-is.
        - strings containing a JSON object or array are decoded. All other strings are returned as-is.
        - ``None`` is returned as an empty string.
        - all other scalars (numbers, booleans) are returned as their JSON string representation.

        :param value: A value from the static data.
        :type value: Any
        :return: The tool call response.
        :rtype: Union[dict, list, str]
        """
        if isinstance(value, (dict, list)):
            return value
        if value is None:
            return ""
        if isinstance(value, str):
            # only decode json objects and arrays. decoding every string would
            # turn values like "42", "true" or "null" into python scalars.
            if value.strip()[:1] in ("{", "["):
                try:
                    decoded = json.loads(value)
                    if isinstance(decoded, (dict, list)):
                        return decoded
                except json.JSONDecodeError:
                    pass
            return value
        return json.dumps(value)

    def tool_call_fetch_plugin_response(
        self, function_args: Union[dict[str, Any], str, None]
    ) -> Union[dict, list, str]:
        """
        Fetch a response from the StaticPlugin based on the provided inquiry type.

        This method retrieves the value associated with the specified ``inquiry_type`` from the plugin's
        static data. It is the handler for the OpenAI function calling tool defined by :attr:`custom_tool`.

        See the OpenAI documentation:
        https://platform.openai.com/docs/assistants/tools/function-calling/quickstart

        The method:

        - Accepts the arguments as a dict, or as the JSON string sent by OpenAI.
        - Ensures that the ``inquiry_type`` argument is present and is a string.
        - Verifies that the plugin is in a ready state and that plugin data is available.
        - Emits ``plugin_called`` when the plugin is called and ``plugin_responded`` when it responds.
        - Looks up the value for the inquiry type in the static data, including in nested dicts.
        - Converts the value to a dict, list or str. See :meth:`to_tool_response`.

        **Example tool call payload:**

        .. code-block:: python

            "tool_calls": [
                {
                    "id": "call_1Ucn2R5WmBh7TtoE197SsP3p",
                    "function": {
                        "arguments": "{\"inquiry_type\":\"couponCodes\"}",  # these are the function_args
                        "name": "smarter_plugin_0000004468"
                    },
                    "type": "function"
                }
            ]

        :param function_args: The function arguments, which must include ``inquiry_type``.
        :type function_args: Union[dict[str, Any], str, None]
        :return: The static data for the inquiry type.
        :rtype: Union[dict, list, str]
        :raises SmarterPluginError: If the arguments are malformed, the inquiry type is missing, not a string or
            not found in the static data, or if the plugin is not ready or lacks data.
        """
        if isinstance(function_args, str):
            try:
                function_args = json.loads(function_args) if function_args.strip() else {}
            except json.JSONDecodeError as e:
                raise SmarterPluginError(
                    f"Plugin {self.name} function_args is not a valid JSON string: {e}.",
                ) from e
        function_args = function_args or {}
        if not isinstance(function_args, dict):
            raise SmarterPluginError(
                f"Plugin {self.name} function_args must be a dict or a JSON string, got {type(function_args)}.",
            )

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
        except SmarterValueError as e:
            raise SmarterPluginError(f"Plugin {self.name} static data is invalid: {e}") from e
        if not isinstance(return_data, dict):
            raise SmarterPluginError(
                f"Plugin {self.name} return data is not a dictionary.",
            )

        found, value = self.find_inquiry_value(return_data, inquiry_type)
        if not found:
            raise SmarterPluginError(
                f"Plugin {self.name} does not have a return value for inquiry_type: {inquiry_type}. Available inquiry types are: {self.inquiry_types}.",
            )
        if value is None:
            logger.warning(
                "%s.tool_call_fetch_plugin_response() plugin %s return value for inquiry_type %s is None. Returning empty string.",
                self.formatted_class_name,
                self.name,
                inquiry_type,
            )

        retval = self.to_tool_response(value)
        plugin_responded.send(
            sender=self.tool_call_fetch_plugin_response,
            plugin=self,
            inquiry_type=inquiry_type,
            response=retval,
        )
        return retval
