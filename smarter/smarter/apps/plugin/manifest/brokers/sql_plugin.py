# pylint: disable=W0718
"""Smarter API SqlPlugin Manifest handler"""

import json
import logging
from typing import Optional, Type

from django.http import HttpRequest

from smarter.apps.plugin.manifest.models.common.plugin.metadata import (
    SAMPluginCommonMetadata,
)
from smarter.apps.plugin.manifest.models.common.plugin.status import (
    SAMPluginCommonStatus,
)
from smarter.apps.plugin.manifest.models.sql_plugin.const import MANIFEST_KIND
from smarter.apps.plugin.manifest.models.sql_plugin.model import SAMSqlPlugin
from smarter.apps.plugin.manifest.models.sql_plugin.spec import (
    Parameter,
    SAMSqlPluginSpec,
    SqlData,
    TestValue,
)
from smarter.apps.plugin.models import PluginDataSql, PluginMeta
from smarter.apps.plugin.plugin.sql import SqlPlugin
from smarter.common.conf import settings as smarter_settings
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


class SAMSqlPluginBroker(SAMPluginBaseBroker):
    """
    Broker for Smarter SQL Plugin Manifests.

    This class is responsible for loading, validating, and parsing Smarter SQL YAML plugin manifests,
    and for initializing the corresponding Pydantic model. It provides generic services for SQL plugins,
    such as instantiation, creation, update, and deletion.

    **Responsibilities:**

      - Load and validate SQL plugin manifests.
      - Parse manifest data into a structured Pydantic model (`SAMSqlPlugin`).
      - Provide access to plugin metadata, status, and specification.
      - Manage plugin lifecycle operations (create, update, delete, etc.).

    **Example Usage:**

    .. code-block:: python

        broker = SAMSqlPluginBroker(manifest=my_manifest)
        plugin = broker.plugin
        if plugin.ready:
            plugin.create()
            plugin.save()

    **Parameters:**

    :param manifest: Optional; a `SAMSqlPlugin` Pydantic model instance representing the plugin manifest.
    :type manifest: Optional[SAMSqlPlugin]

    .. note::
        If the manifest kind does not match the expected plugin kind, or if required fields are missing,
        the broker may raise a `SAMPluginBrokerError` or related exception.

    """

    # override the base abstract manifest model with the Plugin model
    _manifest: Optional[SAMSqlPlugin] = None
    _pydantic_model: Type[SAMSqlPlugin] = SAMSqlPlugin
    _plugin: Optional[SqlPlugin] = None
    _plugin_meta: Optional[PluginMeta] = None
    _plugin_data: Optional[PluginDataSql] = None
    _sql_plugin_spec: Optional[SAMSqlPluginSpec] = None
    _sql_data: Optional[SqlData] = None

    def __init__(self, *args, manifest: Optional[SAMSqlPlugin], **kwargs):
        super().__init__(*args, **kwargs)
        self._manifest = manifest

    def init_plugin(self) -> None:
        """
        Initialize the SQL plugin for this broker.

        This method creates an instance of the `SqlPlugin` class using the current broker's
        metadata, user profile, manifest, and name. It assigns the created plugin to the
        broker's internal `_plugin` attribute for future access.

        :return: None

        **Example:**

        .. code-block:: python

            broker = SAMSqlPluginBroker(manifest=my_manifest)
            broker.init_plugin()
            plugin = broker.plugin
            if plugin.ready:
                plugin.create()
                plugin.save()
        """
        self._manifest = None
        self._plugin = None
        self._plugin_meta = None
        self._plugin_data = None
        self._sql_plugin_spec = None
        self._sql_data = None

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def formatted_class_name(self) -> str:
        """
        Returns a formatted class name for logging.

        This property provides a human-readable, fully qualified class name, which is especially useful for log messages
        and debugging output. The format includes the parent class's formatted name, followed by the current class name.

        :return: A string representing the formatted class name, e.g., ``ParentClass.SAMSqlPluginBroker()``.
        :rtype: str

        **Example:**

        .. code-block:: python

            broker = SAMSqlPluginBroker(manifest=my_manifest)
            print(broker.formatted_class_name)
            # Output: ParentClass.SAMSqlPluginBroker()

        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.{self.__class__.__name__}()"

    @property
    def kind(self) -> str:
        """
        Returns the manifest kind for this plugin broker.

        This property provides the canonical string identifier for the SQL plugin manifest type,
        as defined by the constant ``MANIFEST_KIND``. It is used to distinguish this broker's
        manifest type from others in the Smarter API system.

        :return: The manifest kind string for SQL plugins.
        :rtype: str

        **Example:**

        .. code-block:: python

            broker = SAMSqlPluginBroker(manifest=my_manifest)
            print(broker.kind)
            # Output: "SqlPlugin"  # (or the value of MANIFEST_KIND)

        .. seealso::
            :data:`MANIFEST_KIND`
            :attr:`SAMSqlPluginBroker.manifest`

        """
        return MANIFEST_KIND

    @property
    def manifest(self) -> SAMSqlPlugin:
        """
        Returns the SQL plugin manifest as a validated Pydantic model instance.

        This property constructs and caches a `SAMSqlPlugin` object using data from the manifest loader,
        including API version, kind, metadata, specification, and status. Child models (such as metadata,
        spec, and status) are automatically initialized by Pydantic.

        If the manifest loader's kind matches the expected plugin kind, the manifest is created and cached
        for future access. If the manifest has already been initialized, the cached instance is returned.

        :return: The initialized SQL plugin manifest as a Pydantic model, or ``None`` if not available.
        :rtype: Optional[SAMSqlPlugin]

        **Example:**

        .. code-block:: python

            broker = SAMSqlPluginBroker(manifest=None)
            manifest = broker.manifest
            if manifest:
                print(manifest.apiVersion)

        .. seealso::

            :class:`SAMSqlPlugin`
            :attr:`SAMSqlPluginBroker.kind`
            :class:`SAMPluginCommonMetadata`
            :class:`SAMSqlPluginSpec`
            :class:`SAMPluginCommonStatus`

        """
        if self._manifest:
            return self._manifest

        # If the Plugin has previously been persisted then
        # we can build the manifest components by mapping
        # Django ORM models to Pydantic models.
        if self.plugin_meta:
            metadata = self.plugin_metadata_orm2pydantic()
            sql_data = self.plugin_data_orm2pydantic()
            if not sql_data:
                raise SAMPluginBrokerError(
                    f"{self.formatted_class_name} manifest() failed to build sql_data for {self.kind} {self.plugin_meta.name}",
                    thing=self.kind,
                )
            spec = self.plugin_sql_spec_orm2pydantic()
            if not spec:
                raise SAMPluginBrokerError(
                    f"{self.formatted_class_name} manifest() failed to build spec for {self.kind} {self.plugin_meta.name}",
                    thing=self.kind,
                )
            status = self.plugin_status_pydantic()

            # build the manifest from the
            self._manifest = SAMSqlPlugin(
                apiVersion=self.api_version,
                kind=self.kind,
                metadata=metadata,
                spec=spec,
                status=status,
            )
            return self._manifest
        # Otherwise, if we received a manifest via the loader,
        # then use that to build the manifest.
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMSqlPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMSqlPluginSpec(**self.loader.manifest_spec),
                status=(
                    SAMPluginCommonStatus(**self.loader.manifest_status)
                    if self.loader and self.loader.manifest_status
                    else None
                ),
            )
            return self._manifest

        raise SAMPluginBrokerError(
            f"{self.formatted_class_name} manifest() could not build manifest for {self.kind} {self.plugin_meta.name if self.plugin_meta else 'unknown'}",
            thing=self.kind,
        )

    @property
    def plugin(self) -> Optional[SqlPlugin]:
        """
        Returns the initialized `SqlPlugin` instance for this broker.

        This property creates and caches a `SqlPlugin` object using the current broker's metadata, user profile,
        manifest, and name. If the plugin has already been initialized, the cached instance is returned.

        :return: The initialized `SqlPlugin` instance, or ``None`` if not available.
        :rtype: Optional[SqlPlugin]

        **Example:**

        .. code-block:: python

            broker = SAMSqlPluginBroker(manifest=my_manifest)
            plugin = broker.plugin
            if plugin and plugin.ready:
                plugin.create()
                plugin.save()

        .. seealso::

            :class:`SqlPlugin`
            :attr:`SAMSqlPluginBroker.manifest`
            :attr:`SAMSqlPluginBroker.plugin_meta`

        """
        if self._plugin:
            return self._plugin
        self._plugin = SqlPlugin(
            plugin_meta=self.plugin_meta,
            user_profile=self.user_profile,
            manifest=self.manifest,
            name=self.name,
        )
        return self._plugin

    @property
    def plugin_data(self) -> Optional[PluginDataSql]:
        """
        Returns the `PluginDataSql` ORM object associated with this broker.

        This property retrieves and caches the `PluginDataSql` instance for the current plugin, which is used
        to store and manage plugin-specific data in the database. If the object does not exist, a warning is logged
        and ``None`` is returned.

        :return: The `PluginDataSql` object for this broker, or ``None`` if not available.
        :rtype: Optional[PluginDataSql]

        :raises: :class:`PluginDataSql.DoesNotExist` if the object is not found in the database.

        **Example:**

        .. code-block:: python

            broker = SAMSqlPluginBroker(manifest=my_manifest)
            data = broker.plugin_data
            if data:
                print(data.connection)


        .. seealso::

            :class:`PluginDataSql`
            :attr:`SAMSqlPluginBroker.plugin_meta`

        """
        if self._plugin_data:
            return self._plugin_data

        if self.plugin_meta is None:
            return None

        try:
            self._plugin_data = PluginDataSql.get_cached_data_by_plugin(plugin=self.plugin_meta)
        except PluginDataSql.DoesNotExist:
            logger.warning(
                "%s.plugin_data() PluginDataSql object does not exist for %s %s",
                self.formatted_class_name,
                self.kind,
                self.plugin_meta.name,
            )
        return self._plugin_data

    def plugin_sql_spec_orm2pydantic(self) -> Optional[SAMSqlPluginSpec]:
        """
        Convert the static plugin specification from the Django ORM model format to the Pydantic manifest format.

        This method constructs a `SAMPluginStaticSpec` Pydantic model using the prompt, selector,
        and static data associated with the current `plugin_meta`. It retrieves each component
        using their respective ORM-to-Pydantic conversion methods.

        :return: The static plugin specification as a Pydantic model.
        :rtype: SAMPluginStaticSpec

        **Example:**

        .. code-block:: python

            broker = SAMStaticPluginBroker()
            static_spec = broker.plugin_static_spec_orm2pydantic()
            print(static_spec.model_dump_json())

        :raises SAMPluginBrokerError:
            If there is an error retrieving or converting any component of the plugin specification.


        .. seealso::

            - `SAMPluginStaticSpec`
            - `SAMPluginCommonSpecPrompt`
            - `SAMPluginCommonSpecSelector`
            - `SAMPluginStaticSpecData`
        """
        if self._sql_plugin_spec:
            return self._sql_plugin_spec
        if not self.plugin_meta:
            return None
        selector = self.plugin_selector_orm2pydantic()
        prompt = self.plugin_prompt_orm2pydantic()
        data = self.plugin_data_orm2pydantic()
        if not data:
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} plugin_static_spec_orm2pydantic() failed to build data for {self.kind} {self.plugin_meta.name}",
                thing=self.kind,
            )
        self._sql_plugin_spec = SAMSqlPluginSpec(
            selector=selector,
            prompt=prompt,
            connection=(
                self.plugin_data.connection.name
                if self.plugin_data and self.plugin_data.connection
                else "missing connection"
            ),
            sqlData=data,
        )
        return self._sql_plugin_spec

    def plugin_data_orm2pydantic(self) -> Optional[SqlData]:
        """
        Overrides the parent method to map SQL plugin data from ORM to Pydantic.
        Converts the plugin data from the Django ORM model format to the Pydantic manifest format.

        This method constructs a `SqlData` Pydantic model using the data associated with the current
        `plugin_meta`. It retrieves the data using the ORM-to-Pydantic conversion method.

        :return: The plugin data as a Pydantic model.
        :rtype: SqlData

        **Example:**

        .. code-block:: python

            broker = SAMSqlPluginBroker()
            sql_data = broker.plugin_data_orm2pydantic()
            print(sql_data.model_dump_json())

        :raises SAMPluginBrokerError:
            If there is an error retrieving or converting the plugin data.


        .. seealso::

            - `SqlData`
        """
        if not self.plugin_meta:
            return None

        parameters: list[Parameter] = []
        for parameter in self.plugin_data.parameters.all() if self.plugin_data else []:
            parameters.append(
                Parameter(
                    name=parameter.name,
                    type=parameter.type,
                    description=parameter.description,
                    required=parameter.required,
                    enum=parameter.enum,
                    default=parameter.default,
                )
            )
        test_values: list[TestValue] = []
        for test_value in self.plugin_data.test_values.all() if self.plugin_data else []:
            test_values.append(
                TestValue(
                    name=test_value.name,
                    value=test_value.value,
                )
            )
        self._sql_data = SqlData(
            description=self.plugin_data.description if self.plugin_data else "",
            sqlQuery=self.plugin_data.sql_query if self.plugin_data else "",
            parameters=parameters,
            testValues=test_values,
            limit=self.plugin_data.limit if self.plugin_data else 0,
        )
        return self._sql_data

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Returns an example SQL plugin manifest as a JSON response.

        This method generates a sample manifest for the SQL plugin using the static
        ``example_manifest`` method of the `SqlPlugin` class. The response is wrapped in a
        `SmarterJournaledJsonResponse` for consistency with the Smarter API's journaling and
        response conventions.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments passed to the example manifest generator.
        :return: A JSON response containing the example SQL plugin manifest.
        :rtype: SmarterJournaledJsonResponse

        **Example:**

        .. code-block:: python

            response = broker.example_manifest(request)
            print(response.data)

        .. seealso::

            :meth:`SqlPlugin.example_manifest`
            :class:`SmarterJournaledJsonResponse`

        """
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)
        data = SqlPlugin.example_manifest(kwargs=kwargs)
        return self.json_response_ok(command=command, data=data)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return a JSON response with the manifest data for this SQL plugin.

        This method serializes the current SQL plugin's manifest, metadata, specification, and status
        into a structured JSON response, suitable for API clients or UI inspection. It validates the
        manifest by round-tripping the data through the Pydantic model to ensure schema compliance.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments for customization.
        :return: A `SmarterJournaledJsonResponse` containing the manifest data.
        :rtype: SmarterJournaledJsonResponse

        **Example:**

        .. code-block:: python

            response = broker.describe(request)
            print(response.data)

        :raises SAMPluginBrokerError: If required plugin components are not initialized.
        :raises SAMBrokerErrorNotReady: If the broker is not ready to describe the plugin.

        .. seealso::

            :meth:`SAMSqlPluginBroker.manifest`
            :class:`SmarterJournaledJsonResponse`
            :class:`SAMPluginBrokerError`
            :class:`SAMBrokerErrorNotReady`
            :class:`SqlPlugin`
            :class:`SmarterJournalCliCommands`
            :class:`SAMSqlPlugin`
            :class:`SAMKeys`
            :class:`SqlData`
            :class:`SAMPluginSpecKeys`
            :class:`SAMPluginMeta`

        """
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)

        if not self.manifest:
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} {self.kind} plugin_meta not initialized. Cannot describe",
                thing=self.kind,
                command=command,
            )
        data = json.loads(self.manifest.model_dump_json())
        return self.json_response_ok(command=command, data=data)

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return a JSON response with a list of SQL plugins for this account.

        This method queries the database for all SQL plugins associated with the current account,
        optionally filtered by name, and returns a structured JSON response containing their serialized
        representations. Each plugin is validated by round-tripping through the Pydantic model.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments, such as filter criteria (e.g., ``name``).
        :return: A `SmarterJournaledJsonResponse` containing a list of SQL plugin manifests and metadata.
        :rtype: SmarterJournaledJsonResponse

        **Example:**

        .. code-block:: python

            response = broker.get(request, name="my_plugin")
            print(response.data)

        :raises SAMPluginBrokerError:
            If a plugin cannot be serialized or validated
            during the retrieval process.

        .. seealso::
            :class:`PluginMeta`
            :class:`PluginSerializer`
            :class:`SAMSqlPlugin`
            :class:`SmarterJournaledJsonResponse`
            :class:`SmarterJournalCliCommands`
            :class:`SAMKeys`
            :class:`SAMMetadataKeys`
            :class:`SCLIResponseGet`
            :class:`SCLIResponseGetData`
        """
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)

        data = []
        name = kwargs.get(SAMMetadataKeys.NAME.value)
        name = self.clean_cli_param(param=name, param_name="name", url=self.smarter_build_absolute_uri(request))

        # generate a QuerySet of PluginMeta objects that match our search criteria
        if name:
            plugins = PluginMeta.objects.filter(account=self.account, name=name)
        else:
            plugins = PluginMeta.objects.filter(account=self.account)
        logger.info(
            "%s.get() found %s SqlPlugins for account %s", self.formatted_class_name, plugins.count(), self.account
        )

        # iterate over the QuerySet and use a serializer to create a model dump for each ChatBot
        for plugin in plugins:
            try:
                self.init_plugin()
                self.plugin_meta = plugin

                model_dump = json.loads(self.manifest.model_dump_json())
                if not model_dump:
                    raise SAMPluginBrokerError(
                        f"Model dump failed for {self.kind} {plugin.name}", thing=self.kind, command=command
                    )
                data.append(model_dump)
            except Exception as e:
                logger.error(
                    "%s.get() failed to serialize %s %s",
                    self.formatted_class_name,
                    self.kind,
                    plugin.name,
                    exc_info=True,
                )
                raise SAMPluginBrokerError(
                    f"Failed to serialize {self.kind} {plugin.name}", thing=self.kind, command=command
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
        Apply the manifest: copy manifest data to the Django ORM model and save it to the database.

        This method loads and validates the manifest, then applies its data to the corresponding
        Django ORM model. The plugin is created and, if ready, saved to the database. The response
        includes the serialized plugin data or an error message if the operation fails.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments for customization.
        :return: A `SmarterJournaledJsonResponse` indicating success or failure.
        :rtype: SmarterJournaledJsonResponse

        **Example:**

        .. code-block:: python

            response = broker.apply(request)
            print(response.data)

        :raises SAMPluginBrokerError:
            If the manifest is not set or is not a valid `SAMSqlPlugin`
        :raises SAMBrokerErrorNotReady:
            If the plugin is not ready

        .. seealso::
            :meth:`SAMSqlPluginBroker.manifest`
            :class:`SAMSqlPlugin`
            :class:`SqlPlugin`
            :class:`SmarterJournaledJsonResponse`
            :class:`SAMPluginBrokerError`
            :class:`SAMBrokerErrorNotReady`
        """
        super().apply(request, kwargs)
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)
        if not isinstance(self.manifest, SAMSqlPlugin):
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} {self.plugin_meta.name if self.plugin_meta else '<-- Missing Name -->'} manifest is not set",
                thing=self.kind,
                command=command,
            )
        try:
            self._plugin = SqlPlugin(
                user_profile=self.user_profile,
                manifest=self.manifest,
            )
            if not isinstance(self.plugin, SqlPlugin):
                raise SAMPluginBrokerError(
                    f"{self.formatted_class_name} {self.plugin_meta.name if self.plugin_meta else '<-- Missing Name -->'} is not a SqlPlugin",
                    thing=self.kind,
                    command=command,
                )
            self.plugin.create()
        except Exception as e:
            return self.json_response_err(command=command, e=e)

        if self.plugin.ready:
            try:
                self.plugin.save()
            except Exception as e:
                return self.json_response_err(command=command, e=e)
            return self.json_response_ok(command=command, data=self.to_json())
        try:
            raise SAMBrokerErrorNotReady(
                f"{self.formatted_class_name} {self.plugin_meta.name if self.plugin_meta else self.kind or "SqlPlugin"} not ready",
                thing=self.kind,
                command=command,
            )
        except SAMBrokerErrorNotReady as err:
            return self.json_response_err(command=command, e=err)

    def chat(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Chat with the SQL plugin (not implemented).
        This is not implemented for SQL plugins.

        :raises: SAMBrokerErrorNotImplemented: Always raised to indicate that this method is not implemented.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments (unused).
        :return: A `SmarterJournaledJsonResponse` indicating that the method is not implemented.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="chat() not implemented", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Delete the SQL plugin.
        This method deletes the SQL plugin associated with this broker. It verifies that the plugin
        is of the correct type and is ready before attempting deletion. If successful, it returns a
        JSON response indicating success; otherwise, it raises appropriate errors.

        :raises: SAMPluginBrokerError: If the plugin or plugin metadata is not properly initialized.
        :raises: SAMBrokerErrorNotReady: If the plugin is not ready for deletion.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments (unused).
        :return: A `SmarterJournaledJsonResponse` indicating success or failure of the deletion.
        :rtype: SmarterJournaledJsonResponse

        .. seealso::

            :class:`SqlPlugin`
            :class:`SmarterJournaledJsonResponse`
            :class:`SAMPluginBrokerError`
            :class:`SAMBrokerErrorNotReady`
            :class:`SmarterJournalCliCommands`

        """
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        self.set_and_verify_name_param(command=command)
        if not isinstance(self.plugin, SqlPlugin):
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} {self.plugin_meta.name if self.plugin_meta else '<-- Missing Name -->'} delete() not implemented for {self.kind}",
                thing=self.kind,
                command=command,
            )
        if not isinstance(self.plugin_meta, PluginMeta):
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} <-- Missing Name --> delete() not implemented for {self.kind}",
                thing=self.kind,
                command=command,
            )
        if not self.plugin.ready:
            raise SAMBrokerErrorNotReady(
                f"{self.formatted_class_name} {self.plugin_meta.name} not ready", thing=self.kind, command=command
            )
        try:
            self.plugin.delete()
            return self.json_response_ok(command=command, data={})
        except Exception as e:
            raise SAMBrokerError(
                f"{self.formatted_class_name} {self.plugin_meta.name} delete failed",
                thing=self.kind,
                command=command,
            ) from e

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Deploy the SQL plugin (not implemented).
        This is not implemented for SQL plugins.

        :raises: SAMBrokerErrorNotImplemented: Always raised to indicate that this method is not implemented.
        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments (unused).
        :return: A `SmarterJournaledJsonResponse` indicating that the method is not implemented.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("deploy() not implemented", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Undeploy the SQL plugin (not implemented).
        This is not implemented for SQL plugins.

        :raises: SAMBrokerErrorNotImplemented: Always raised to indicate that this method is not implemented.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments (unused).
        :return: A `SmarterJournaledJsonResponse` indicating that the method is not implemented.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("undeploy() not implemented", thing=self.kind, command=command)

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Retrieve logs for the SQL plugin (not implemented).
        This is not implemented for SQL plugins.

        :raises: SAMBrokerErrorNotImplemented: Always raised to indicate that this method is not implemented.
        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments (unused).
        :return: A `SmarterJournaledJsonResponse` indicating that the method is not implemented.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("logs() not implemented", thing=self.kind, command=command)
