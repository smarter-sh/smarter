# pylint: disable=W0718
"""Smarter API StaticPlugin Manifest handler"""

import logging
from typing import Optional, Type

from django.forms.models import model_to_dict
from django.http import HttpRequest

from smarter.apps.plugin.manifest.enum import (
    SAMPluginSpecKeys,
    SAMStaticPluginSpecDataKeys,
)
from smarter.apps.plugin.manifest.models.common.plugin.metadata import (
    SAMPluginCommonMetadata,
)
from smarter.apps.plugin.manifest.models.common.plugin.spec import (
    SAMPluginCommonSpecPrompt,
    SAMPluginCommonSpecSelector,
)
from smarter.apps.plugin.manifest.models.static_plugin.const import MANIFEST_KIND
from smarter.apps.plugin.manifest.models.static_plugin.model import SAMStaticPlugin
from smarter.apps.plugin.manifest.models.static_plugin.spec import (
    SAMPluginStaticSpec,
    SAMPluginStaticSpecData,
)
from smarter.apps.plugin.models import (
    PluginDataStatic,
    PluginMeta,
    PluginPrompt,
    PluginSelector,
)
from smarter.apps.plugin.plugin.static import StaticPlugin
from smarter.common.conf import settings as smarter_settings
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.broker import (
    SAMBrokerError,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
)
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
    SCLIResponseGetData,
)

from . import PluginSerializer, SAMPluginBrokerError
from .plugin_base import SAMPluginBaseBroker


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)
        or waffle.switch_is_active(SmarterWaffleSwitches.MANIFEST_LOGGING)
    ) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class SAMStaticPluginBroker(SAMPluginBaseBroker):
    """
    Broker for Smarter API StaticPlugin manifests.

    This class is responsible for loading, validating, and parsing Smarter API YAML StaticPlugin manifests,
    and initializing the corresponding Pydantic model. It provides generic services for StaticPlugins,
    such as instantiation, creation, update, and deletion.

    **Responsibilities:**

      - Load and validate StaticPlugin manifests.
      - Parse manifest data and initialize the `SAMStaticPlugin` Pydantic model.
      - Manage plugin lifecycle: create, update, delete, and describe.
      - Interface with Django ORM models for plugin metadata, prompt, selector, and static data.

    **Parameters:**

      - `loader`: Manifest loader instance (must match expected manifest kind).
      - `plugin_meta`: Django ORM model for plugin metadata.
      - `plugin_data`: Django ORM model for static plugin data.
      - `user_profile`: User profile associated with the plugin.
      - `name`: Plugin name.

    **Example Manifest Response:**

    .. code-block:: json

        {
            "apiVersion": "smarter.sh/v1",
            "kind": "Plugin",
            "metadata": {
                "name": "cli_test_plugin",
                "description": "...",
                "version": "0.2.0",
                "tags": [],
                "annotations": null,
                "pluginClass": "static"
            },
            "spec": {
                "prompt": { },
                "selector": { },
                "data": { }
            },
            "status": {
                "created": "2025-06-24T21:38:36.368058+00:00",
                "modified": "2025-06-24T21:38:36.434526+00:00"
            }
        }

    .. seealso::

        - `SAMPluginBaseBroker` for base broker functionality.
        - `SAMStaticPlugin` for the manifest model.
        - Django ORM models: `PluginMeta`, `PluginDataStatic`, `PluginPrompt`, `PluginSelector`.

    """

    # override the base abstract manifest model with the StaticPlugin model
    _manifest: Optional[SAMStaticPlugin] = None
    _pydantic_model: Type[SAMStaticPlugin] = SAMStaticPlugin
    _plugin_data: Optional[PluginDataStatic] = None
    _plugin: Optional[StaticPlugin] = None

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def formatted_class_name(self) -> str:
        """
        Returns a formatted class name for logging.

        This property provides a human-readable class name string, combining the parent class name
        (from `super().formatted_class_name`) with the current class name. This is useful for
        log messages, debugging, and tracing execution in complex broker hierarchies.

        :return: Formatted class name string, e.g. ``BaseBroker.SAMStaticPluginBroker()``
        :rtype: str

        **Example:**

        .. code-block:: python

            broker = SAMStaticPluginBroker()
            print(broker.formatted_class_name)
            # Output: BaseBroker.SAMStaticPluginBroker()

        .. seealso::
            - `SAMPluginBaseBroker.formatted_class_name`

        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.{self.__class__.__name__}()"

    @property
    def kind(self) -> str:
        """
        Returns the manifest kind for this broker.

        This property provides the manifest kind string, which is used to identify the type of plugin manifest
        handled by this broker. For static plugins, this is typically set to ``MANIFEST_KIND``.

        :return: Manifest kind string (e.g. ``"Plugin"``)
        :rtype: str

        **Example:**

        .. code-block:: python

            broker = SAMStaticPluginBroker()
            print(broker.kind)
            # Output: "Plugin"


        .. seealso::

            - `MANIFEST_KIND` constant in `smarter.apps.plugin.manifest.models.static_plugin.const`
            - `SAMStaticPluginBroker.manifest`

        """
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMStaticPlugin]:
        """
        Returns the manifest for the static plugin as a Pydantic model instance.

        This property initializes and returns a `SAMStaticPlugin` object, representing the full manifest for a static plugin.
        The manifest is built using data from the manifest loader, including API version, kind, metadata, and specification.
        Child models (such as metadata and spec) are automatically initialized by Pydantic using the provided data.

        :return: The initialized static plugin manifest as a Pydantic model, or None if not available.
        :rtype: Optional[SAMStaticPlugin]

        **Example:**

        .. code-block:: python

            broker = SAMStaticPluginBroker()
            manifest = broker.manifest
            if manifest:
                print(manifest.model_dump_json())

        .. seealso::

            - `SAMStaticPlugin`
            - `SAMPluginCommonMetadata`
            - `SAMPluginStaticSpec`

        """
        if self._manifest:
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMStaticPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMPluginStaticSpec(**self.loader.manifest_spec),
            )
        return self._manifest

    @property
    def plugin(self) -> Optional[StaticPlugin]:
        """
        Returns the `StaticPlugin` instance managed by this broker.

        This property lazily initializes and returns a `StaticPlugin` object, using the current plugin metadata,
        user profile, manifest, and name. If the plugin has already been initialized, the cached instance is returned.

        :return: The managed `StaticPlugin` instance, or None if initialization fails.
        :rtype: Optional[StaticPlugin]

        **Example:**

        .. code-block:: python

            broker = SAMStaticPluginBroker()
            plugin = broker.plugin
            if plugin:
                print(plugin.name)

        .. seealso::

            - `StaticPlugin`
            - `SAMStaticPluginBroker.manifest`
            - `SAMStaticPluginBroker.plugin_meta`
        """
        if self._plugin:
            return self._plugin
        self._plugin = StaticPlugin(
            plugin_meta=self.plugin_meta,
            user_profile=self.user_profile,
            manifest=self.manifest,
            name=self.name,
        )
        return self._plugin

    @property
    def plugin_data(self) -> Optional[PluginDataStatic]:
        """
        Returns the `PluginDataStatic` object for this broker.

        This property retrieves the static plugin data from the database, using the associated `plugin_meta`.
        If the data has already been loaded, the cached instance is returned. If `plugin_meta` is not set,
        this property returns None.

        :return: The `PluginDataStatic` instance for this plugin, or None if not available.
        :rtype: Optional[PluginDataStatic]

        **Example:**

        .. code-block:: python

            broker = SAMStaticPluginBroker()
            data = broker.plugin_data
            if data:
                print(data.some_field)

        :raises SAMPluginBrokerError:
            If there is an error retrieving the plugin data from the database.


        .. seealso::

            - `PluginDataStatic`
            - `SAMStaticPluginBroker.plugin_meta`
        """
        if self._plugin_data:
            return self._plugin_data

        if self.plugin_meta is None:
            return None

        try:
            self._plugin_data = PluginDataStatic.objects.get(plugin=self.plugin_meta)
        except PluginDataStatic.DoesNotExist:
            logger.warning(
                "%s.plugin_data() PluginDataStatic object does not exist for %s %s",
                self.formatted_class_name,
                self.kind,
                self.plugin_meta.name,
            )
        return self._plugin_data

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return an example manifest for a static plugin.

        This method generates and returns a sample manifest structure for a static plugin, using
        `StaticPlugin.example_manifest`. The response is wrapped in a `SmarterJournaledJsonResponse`
        for consistent API output.

        :param request: Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments passed to the manifest generator.
        :return: JSON response containing the example manifest.
        :rtype: SmarterJournaledJsonResponse

        **Example:**

        .. code-block:: python

            response = broker.example_manifest(request, foo="bar")
            print(response.data)


        .. seealso::

            - `StaticPlugin.example_manifest`
            - `SmarterJournaledJsonResponse`
            - `SmarterJournalCliCommands`


        """
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)
        data = StaticPlugin.example_manifest(kwargs=kwargs)
        return self.json_response_ok(command=command, data=data)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Serialize and return the manifest for a static plugin as a JSON response.

        This method collects and validates all required components of a static plugin manifest, including metadata,
        prompt configuration, selector criteria, and static data. It ensures that all plugin objects are present and
        ready, and provides informative error responses if any required component is missing or invalid.

        The returned manifest contains the following top-level fields:

        - ``apiVersion``: Manifest API version string.
        - ``kind``: Manifest kind (usually "Plugin").
        - ``metadata``: Plugin metadata (name, description, version, tags, annotations, plugin class).
        - ``spec``: Specification details (prompt configuration, selector criteria, static plugin data).
        - ``status``: Creation and last modification timestamps.

        Example response:

        .. code-block:: json

           {
               "apiVersion": "smarter.sh/v1",
               "kind": "Plugin",
               "metadata": {
                   "name": "cli_test_plugin",
                   "description": "...",
                   "version": "0.2.0",
                   "tags": [],
                   "annotations": null,
                   "pluginClass": "static"
               },
               "spec": {
                   "prompt": {  },
                   "selector": {  },
                   "data": {  }
               },
               "status": {
                   "created": "2025-06-24T21:38:36.368058+00:00",
                   "modified": "2025-06-24T21:38:36.434526+00:00"
               }
           }

        Error handling:
            - If the plugin is not found or not ready, a ``SAMBrokerErrorNotReady`` is raised.
            - If required plugin metadata, selector, or prompt objects are missing or invalid, a ``SAMPluginBrokerError`` is raised.
            - Any unexpected errors during manifest serialization will raise a generic ``Exception``.

        Returns
        -------
        SmarterJournaledJsonResponse
            JSON response containing the plugin manifest or error details.

        .. seealso::

            - `SAMPluginCommonMetadata`
            - `SAMPluginCommonSpecPrompt`
            - `SAMPluginCommonSpecSelector`
            - `SAMPluginStaticSpecData`
            - `SmarterJournaledJsonResponse`
            - `SmarterJournalCliCommands`
            - :class:`SAMKeys`
            - :class:`SAMPluginSpecKeys`
            - :class:`SAMStaticPluginSpecDataKeys`



        """
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)

        if not isinstance(self.plugin, StaticPlugin):
            raise SAMBrokerErrorNotReady(
                message=f"No plugin found. url: {request.build_absolute_uri()}, args={json.dumps(args)}, kwargs={json.dumps(kwargs)}",
                thing=self.kind,
                command=command,
            )
        if self.account is None:
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} {self.kind} account not initialized. Cannot describe",
                thing=self.kind,
                command=command,
            )
        if not isinstance(self.plugin_meta, PluginMeta):
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} {self.kind} plugin_meta not initialized. Cannot describe",
                thing=self.kind,
                command=command,
            )

        # metadata
        try:
            metadata = model_to_dict(self.plugin_meta)  # type: ignore[no-any-return]
            metadata = self.snake_to_camel(metadata)
            if not isinstance(metadata, dict):
                raise SAMPluginBrokerError(
                    f"Model dump failed for {self.kind} {self.plugin.name}",
                    thing=self.kind,
                    command=command,
                )
            metadata = SAMPluginCommonMetadata(**metadata)
        except PluginMeta.DoesNotExist:
            return self.json_response_err(
                command=command,
                e=SAMPluginBrokerError(
                    f"{self.formatted_class_name} {self.kind} PluginMeta does not exist for {self.plugin.name}",
                    thing=self.kind,
                    command=command,
                ),
            )
        except Exception as e:
            raise SAMPluginBrokerError(message=str(e), thing=self.kind, command=command) from e

        # PluginSelector
        try:
            plugin_selector = PluginSelector.objects.get(plugin=self.plugin_meta)
            plugin_selector = model_to_dict(plugin_selector)  # type: ignore[no-any-return]
            plugin_selector = self.snake_to_camel(plugin_selector)
            if not isinstance(plugin_selector, dict):
                raise SAMPluginBrokerError(
                    f"Model dump failed for {self.kind} {self.plugin.name}",
                    thing=self.kind,
                    command=command,
                )
            plugin_selector = SAMPluginCommonSpecSelector(**plugin_selector)
        except PluginSelector.DoesNotExist:
            return self.json_response_err(
                command=command,
                e=SAMPluginBrokerError(
                    f"{self.formatted_class_name} {self.kind} PluginSelector does not exist for {self.plugin_meta.name}",
                    thing=self.kind,
                    command=command,
                ),
            )
        except Exception as e:
            raise SAMPluginBrokerError(message=str(e), thing=self.kind, command=command) from e

        # PluginPrompt
        try:
            plugin_prompt = PluginPrompt.objects.get(plugin=self.plugin_meta)
            plugin_prompt = model_to_dict(plugin_prompt)  # type: ignore[no-any-return]
            plugin_prompt = self.snake_to_camel(plugin_prompt)
            if not isinstance(plugin_prompt, dict):
                raise SAMPluginBrokerError(
                    f"Model dump failed for {self.kind} {self.plugin.name}",
                    thing=self.kind,
                    command=command,
                )
            plugin_prompt = SAMPluginCommonSpecPrompt(**plugin_prompt)
        except PluginPrompt.DoesNotExist:
            return self.json_response_err(
                command=command,
                e=SAMPluginBrokerError(
                    f"{self.formatted_class_name} {self.kind} PluginPrompt does not exist for {self.plugin_meta.name}",
                    thing=self.kind,
                    command=command,
                ),
            )
        except Exception as e:
            raise SAMPluginBrokerError(message=str(e), thing=self.kind, command=command) from e

        # PluginData
        try:
            plugin_data = model_to_dict(self.plugin_data)  # type: ignore[no-any-return]
            plugin_data = self.snake_to_camel(plugin_data)
            if not isinstance(plugin_data, dict):
                raise SAMPluginBrokerError(
                    f"Model dump failed for {self.kind} {self.plugin.name}",
                    thing=self.kind,
                    command=command,
                )
            plugin_data = SAMPluginStaticSpecData(**plugin_data)
        except Exception as e:
            raise SAMPluginBrokerError(message=str(e), thing=self.kind, command=command) from e

        try:
            retval = {
                SAMKeys.APIVERSION.value: self.api_version,
                SAMKeys.KIND.value: self.kind,
                SAMKeys.METADATA.value: metadata.model_dump(),
                SAMKeys.SPEC.value: {
                    SAMPluginSpecKeys.PROMPT.value: plugin_prompt.model_dump(),
                    SAMPluginSpecKeys.SELECTOR.value: plugin_selector.model_dump(),
                    SAMPluginSpecKeys.DATA.value: {
                        SAMStaticPluginSpecDataKeys.DESCRIPTION.value: self.plugin_meta.description,
                        SAMStaticPluginSpecDataKeys.STATIC.value: plugin_data.model_dump(),
                    },
                },
                SAMKeys.STATUS.value: {
                    "created": self.plugin_meta.created_at.isoformat(),
                    "modified": self.plugin_meta.updated_at.isoformat(),
                },
            }
            # validate our results by round-tripping the data through the Pydantic model
            pydantic_model = self.pydantic_model(**retval)
            pydantic_model.model_dump_json()
            return self.json_response_ok(command=command, data=retval)
        except Exception as e:
            logger.error(
                "%s.describe() failed to serialize %s %s",
                self.formatted_class_name,
                self.kind,
                self.plugin.name,
                exc_info=True,
            )
            raise SAMPluginBrokerError(
                f"Failed to serialize {self.kind} {self.plugin.name}", thing=self.kind, command=command
            ) from e

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Retrieve static plugins based on search criteria.

        This method queries the database for static plugins associated with the current account.
        If a plugin name is provided in `kwargs`, only plugins matching that name are returned.
        The results are serialized and returned in a `SmarterJournaledJsonResponse`, including metadata
        such as count and titles.

        :param request: Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Search criteria, e.g. plugin name.
        :return: JSON response containing serialized plugin data and metadata.
        :rtype: SmarterJournaledJsonResponse

        **Example:**

        .. code-block:: python

            response = broker.get(request, name="cli_test_plugin")
            print(response.data)

        .. seealso::

            - `PluginMeta`
            - `PluginSerializer`
            - `SmarterJournaledJsonResponse`
        """
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)

        data = []
        name = kwargs.get(SAMMetadataKeys.NAME.value)
        name = self.clean_cli_param(param=name, param_name="name", url=self.smarter_build_absolute_uri(request))

        # generate a QuerySet of PluginMeta objects that match our search criteria
        if name:
            chatbots = PluginMeta.objects.filter(account=self.account, name=name)
        else:
            chatbots = PluginMeta.objects.filter(account=self.account)
        logger.info(
            "%s.get() found %s Plugins for account %s", self.formatted_class_name, chatbots.count(), self.account
        )

        # iterate over the QuerySet and use a serializer to create a model dump for each ChatBot
        for chatbot in chatbots:
            try:
                model_dump = PluginSerializer(chatbot).data
                if not model_dump:
                    raise SAMPluginBrokerError(
                        f"Model dump failed for {self.kind} {chatbot.name}", thing=self.kind, command=command
                    )
                camel_cased_model_dump = self.snake_to_camel(model_dump)
                data.append(camel_cased_model_dump)
            except Exception as e:
                logger.error(
                    "%s.get() failed to serialize %s %s",
                    self.formatted_class_name,
                    self.kind,
                    chatbot.name,
                    exc_info=True,
                )
                raise SAMPluginBrokerError(
                    f"Failed to serialize {self.kind} {chatbot.name}", thing=self.kind, command=command
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: name,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=PluginSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Apply the manifest to the database.

        This method copies the manifest data to the Django ORM model and saves it to the database.
        It first ensures the manifest is loaded and validated by calling the base class's `apply` method.
        If the plugin or its metadata is not properly initialized, an error is raised.

        :param request: Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments for manifest application.
        :return: JSON response indicating success or error details.
        :rtype: SmarterJournaledJsonResponse

        **Example:**

        .. code-block:: python

            response = broker.apply(request, name="cli_test_plugin")
            print(response.data)

        :raises SAMPluginBrokerError:
            If the plugin or plugin metadata is not initialized
        :raises SAMBrokerErrorNotReady:
            If the plugin is not ready after creation


        .. seealso::

            - `SAMPluginBaseBroker.apply`
            - `StaticPlugin.create`
            - `StaticPlugin.save`
            - `SmarterJournaledJsonResponse`
        """
        super().apply(request, kwargs)
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)
        if not isinstance(self.plugin, StaticPlugin):
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} {self.kind} plugin not initialized. Cannot apply",
                thing=self.kind,
                command=command,
            )
        if not isinstance(self.plugin_meta, PluginMeta):
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} {self.kind} plugin_meta not initialized. Cannot apply",
                thing=self.kind,
                command=command,
            )

        try:
            self.plugin.create()
        except Exception as e:
            logger.error(
                "%s.apply() failed to create %s %s",
                self.formatted_class_name,
                self.kind,
                self.plugin_meta.name,
                exc_info=True,
            )
            return self.json_response_err(command=command, e=e)

        if self.plugin.ready:
            try:
                self.plugin.save()
            except Exception as e:
                return self.json_response_err(command=command, e=e)
            return self.json_response_ok(command=command, data=self.to_json())
        try:
            raise SAMBrokerErrorNotReady(
                f"{self.formatted_class_name} {self.plugin_meta.name} not ready", thing=self.kind, command=command
            )
        except SAMBrokerErrorNotReady as err:
            logger.error(
                "%s.apply() failed to save %s %s",
                self.formatted_class_name,
                self.kind,
                self.plugin_meta.name,
                exc_info=True,
            )
            return self.json_response_err(command=command, e=err)

    def chat(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Chat with the static plugin (not implemented).

        :raises SAMBrokerErrorNotImplemented:
            Always raised to indicate that this method is not implemented.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: JSON response indicating error.
        :rtype: SmarterJournaledJsonResponse
        """
        super().chat(request, kwargs)
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="chat() not implemented", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Delete the static plugin.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: JSON response indicating success or error.
        :rtype: SmarterJournaledJsonResponse

        :raises SAMPluginBrokerError:
            If the plugin or plugin metadata is not initialized.
        :raises SAMBrokerErrorNotReady:
            If the plugin is not ready to be deleted.

        .. seealso::

            - `StaticPlugin.delete`
            - `SmarterJournaledJsonResponse`
            - :meth:`SAMPluginBaseBroker.set_and_verify_name_param`

        """
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        self.set_and_verify_name_param(command=command)
        if not isinstance(self.plugin, StaticPlugin):
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} {self.kind} plugin not initialized. Cannot delete",
                thing=self.kind,
                command=command,
            )
        if not isinstance(self.plugin_meta, PluginMeta):
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} {self.kind} plugin_meta not initialized. Cannot delete",
                thing=self.kind,
                command=command,
            )
        if self.plugin.ready:
            try:
                self.plugin.delete()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                raise SAMBrokerError(
                    f"{self.formatted_class_name} {self.plugin_meta.name} delete failed",
                    thing=self.kind,
                    command=command,
                ) from e
        raise SAMBrokerErrorNotReady(
            f"{self.formatted_class_name} {self.plugin_meta.name} not ready", thing=self.kind, command=command
        )

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Deploy the static plugin (not implemented).

        :raises SAMBrokerErrorNotImplemented:
            Always raised to indicate that this method is not implemented.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: JSON response indicating error.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("deploy() not implemented", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Undeploy the static plugin (not implemented).

        :raises SAMBrokerErrorNotImplemented:
            Always raised to indicate that this method is not implemented.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: JSON response indicating error.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("undeploy() not implemented", thing=self.kind, command=command)

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Retrieve logs for the static plugin (not implemented).

        :raises SAMBrokerErrorNotImplemented:
            Always raised to indicate that this method is not implemented.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: JSON response indicating error.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("logs() not implemented", thing=self.kind, command=command)
