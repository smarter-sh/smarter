# pylint: disable=W0718
"""Smarter API ApiPlugin Manifest handler"""

import logging
from typing import TYPE_CHECKING, Optional, Type

from smarter.apps.account.utils import get_cached_admin_user_for_account
from smarter.apps.plugin.manifest.models.api_plugin.const import MANIFEST_KIND
from smarter.apps.plugin.manifest.models.api_plugin.model import SAMApiPlugin
from smarter.apps.plugin.manifest.models.api_plugin.spec import (
    ApiData,
    SAMApiPluginSpec,
)
from smarter.apps.plugin.manifest.models.common import (
    Parameter,
    RequestHeader,
    TestValue,
    UrlParam,
)
from smarter.apps.plugin.manifest.models.common.plugin.metadata import (
    SAMPluginCommonMetadata,
)
from smarter.apps.plugin.models import PluginDataApi, PluginMeta
from smarter.apps.plugin.plugin.api import ApiPlugin
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

from . import SAMPluginBrokerError
from .plugin_base import SAMPluginBaseBroker

if TYPE_CHECKING:
    from django.http import HttpRequest


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) or waffle.switch_is_active(
        SmarterWaffleSwitches.MANIFEST_LOGGING
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class SAMApiPluginBroker(SAMPluginBaseBroker):
    """
    Smarter API ApiPlugin Manifest (SAM) Broker.

    This broker class is responsible for:

      - Loading, validating, and parsing Smarter API YAML `ApiPlugin` manifests.
      - Initializing the corresponding Pydantic model from manifest data.
      - Providing generic services for `ApiPlugin` objects, including instantiation, creation, update, and deletion.

    :param loader: Manifest loader providing manifest data.
    :type loader: Optional[ManifestLoader]
    :param account: The account context for the plugin.
    :type account: Account
    :param user_profile: The user profile associated with the plugin.
    :type user_profile: UserProfile

    .. important::

        This broker ensures that plugin manifests are validated and structured before any database or API operations.

    .. note::

        The manifest is cached after initialization.


    .. seealso::

        :class:`SAMApiPlugin`
        :class:`ApiPlugin`
        :class:`PluginDataApi`
        :class:`PluginMeta`
        :class:`SAMPluginBrokerError`

    **Example usage**::

        broker = SAMApiPluginBroker(loader=my_loader, account=my_account, user_profile=my_profile)
        manifest = broker.manifest
        plugin = broker.plugin
        plugin_data = broker.plugin_data


    """

    # override the base abstract manifest model with the ApiPlugin model
    _plugin: Optional[ApiPlugin] = None
    _plugin_data: Optional[PluginDataApi] = None
    _manifest: Optional[SAMApiPlugin] = None
    _pydantic_model: Type[SAMApiPlugin] = SAMApiPlugin
    _plugin_meta: Optional[PluginMeta] = None
    _api_data: Optional[ApiData] = None
    _sql_plugin_spec: Optional[SAMApiPluginSpec] = None

    def __init__(self, *args, **kwargs):
        """
        Initialize the SAMApiPluginBroker instance.

        This constructor initializes the broker by calling the parent class's
        constructor, which will attempt to bootstrap the class instance
        with any combination of raw manifest data (in JSON or YAML format),
        a manifest loader, or existing Django ORM models. If a manifest
        loader is provided and its kind matches the expected kind for this broker,
        the manifest is initialized using the loader's data.

        This class can bootstrap itself in any of the following ways:

        - request.body (yaml or json string)
        - name + account (determined via authentication of the request object)
        - SAMLoader instance
        - manifest instance
        - filepath to a manifest file

        If raw manifest data is provided, whether as a string or a dictionary,
        or a SAMLoader instance, the base class constructor will only goes as
        far as initializing the loader. The actual manifest model initialization
        is deferred to this constructor, which checks the loader's kind.

        :param args: Positional arguments passed to the parent constructor.
        :param kwargs: Keyword arguments passed to the parent constructor.

        **Example:**

        .. code-block:: python

            broker = SAMApiPluginBroker(loader=loader, plugin_meta=plugin_meta)

        .. seealso::
            - `SAMPluginBaseBroker.__init__`
        """
        super().__init__(*args, **kwargs)
        if not self.ready:
            if not self.loader and not self.manifest and not self.plugin:
                logger.warning(
                    "%s.__init__() No loader nor existing Plugin provided for %s broker. Cannot initialize.",
                    self.formatted_class_name,
                    self.kind,
                )
                return
            if self.loader and self.loader.manifest_kind != self.kind:
                raise SAMBrokerErrorNotReady(
                    f"Loader manifest kind {self.loader.manifest_kind} does not match broker kind {self.kind}",
                    thing=self.kind,
                )

            if self.loader:
                self._manifest = SAMApiPlugin(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                    spec=SAMApiPluginSpec(**self.loader.manifest_spec),
                )
            if self._manifest:
                logger.info(
                    "%s.__init__() initialized manifest from loader for %s %s",
                    self.formatted_class_name,
                    self.kind,
                    self.manifest.metadata.name,
                )
        msg = f"{self.formatted_class_name}.__init__() broker for {self.kind} {self.name} is {self.ready_state}."
        if self.ready:
            logger.info(msg)
        else:
            logger.warning(msg)

    def plugin_init(self) -> None:
        """
        Initialize the plugin metadata for this broker.

        This method retrieves and caches the `PluginMeta` object associated with the current account and plugin name.
        If the plugin metadata does not exist, it logs a warning.

        :return: None

        """
        super().plugin_init()
        self._plugin = None
        self._plugin_data = None
        self._manifest = None
        self._plugin_meta = None
        self._api_data = None
        self._sql_plugin_spec = None

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def ORMModelClass(self) -> Type[PluginMeta]:
        """
        Return the Django ORM model class for the broker.

        :return: The Django ORM model class definition for the broker.
        :rtype: Type[PluginMeta]
        """
        return PluginMeta

    @property
    def SAMModelClass(self) -> Type[SAMApiPlugin]:
        """
        Return the Pydantic model class for the broker.

        :return: The Pydantic model class definition for the broker.
        :rtype: Type[SAMApiPlugin]
        """
        return SAMApiPlugin

    @property
    def formatted_class_name(self) -> str:
        """
        Return a human-readable, fully qualified class name for logging.

        This property generates a formatted class name string, combining the parent class name and the current class, to improve log traceability and clarity. It is especially useful for distinguishing log entries in complex inheritance hierarchies.

        :return: Formatted class name string for use in logs.
        :rtype: str

        .. seealso::

            :meth:`SAMPluginBaseBroker.formatted_class_name`

        **Example usage**::

            logger.info("%s: plugin operation started", broker.formatted_class_name)

        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.{SAMApiPluginBroker.__name__}[{id(self)}]"

    @property
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMApiPlugin]:
        """
        Initializes and returns the manifest for the API plugin as a Pydantic model instance.

        This property constructs a `SAMApiPlugin` object using data provided by the manifest loader, including API version,
        kind, metadata, and specification. The top-level manifest model is explicitly initialized, while child models
        (such as metadata and spec) are automatically cascade-initialized by Pydantic using the relevant data.

        If the manifest loader's kind matches the expected plugin kind, the manifest is created and cached for future access.
        If the manifest has already been initialized, the cached instance is returned.

        The resulting manifest object provides a validated, structured representation of the API plugin manifest, suitable for
        further processing, serialization, or validation within the Smarter API system.

        Returns
        -------
        Optional[SAMApiPlugin]
            The initialized API plugin manifest as a Pydantic model, or None if not available.

        .. seealso::

            :class:`SAMApiPlugin`
            :class:`SAMPluginBaseBroker.manifest`
            :class:`SAMApiPluginSpec`
            :class:`SAMPluginCommonMetadata`

        """
        if self._manifest:
            if not isinstance(self._manifest, SAMApiPlugin):
                raise SAMPluginBrokerError(
                    f"Invalid manifest type for {self.kind} broker: {type(self._manifest)}",
                    thing=self.kind,
                )
            return self._manifest

        # 1.) prioritize manifest loader data if available. if it was provided
        #     in the request body then this is the authoritative source.
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiPluginSpec(**self.loader.manifest_spec),
            )

        # 2.) next, (and only if a loader is not available) try to initialize
        #     from existing Account model if available
        elif self._plugin_meta:
            metadata = self.plugin_metadata_orm2pydantic()
            status = self.plugin_status_pydantic()
            api_data = self.plugin_data_orm2pydantic()
            if not api_data:
                raise SAMPluginBrokerError(
                    f"{self.formatted_class_name} No plugin data found for {self.kind} {self.plugin_meta.name}",
                    thing=self.kind,
                )

            spec = self.plugin_sql_spec_orm2pydantic()
            if not spec:
                raise SAMPluginBrokerError(
                    f"{self.formatted_class_name} No plugin spec found for {self.kind} {self.plugin_meta.name}",
                    thing=self.kind,
                )

            admin = get_cached_admin_user_for_account(self.plugin_meta.user_profile.account)
            if not admin:
                raise SAMPluginBrokerError(
                    f"{self.formatted_class_name} No admin user found for account {self.plugin_meta.user_profile.account}",
                    thing=self.kind,
                )
            self._manifest = SAMApiPlugin(
                apiVersion=self.api_version,
                kind=self.kind,
                metadata=metadata,
                spec=spec,
                status=status,
            )
            return self._manifest
        else:
            logger.warning("%s.manifest could not be initialized", self.formatted_class_name)
        return self._manifest

    @property
    def plugin(self) -> Optional[ApiPlugin]:
        if self._plugin:
            return self._plugin
        self._plugin = ApiPlugin(
            plugin_meta=self.plugin_meta,
            user_profile=self.user_profile,
            manifest=self._manifest,
            name=self.name,
        )
        return self._plugin

    @property
    def plugin_data(self) -> Optional[PluginDataApi]:
        """
        Retrieve the `PluginDataApi` object associated with this broker.

        This property is used to access and store plugin-specific data in the database. If the plugin metadata is not initialized, it returns `None`. If the data object does not exist, a warning is logged.

        :return: The `PluginDataApi` instance for this broker, or `None` if unavailable.
        :rtype: Optional[PluginDataApi]

        .. warning::

            If the `PluginDataApi` object does not exist for the given plugin, a warning is logged and `None` is returned.

        .. seealso::

            :class:`PluginDataApi`
            :class:`PluginMeta`
            :meth:`SAMApiPluginBroker.plugin_meta`

        **Example usage**::

            plugin_data = broker.plugin_data
            if plugin_data:
                print(plugin_data.connection)
            else:
                print("No plugin data found.")


        """
        if self._plugin_data:
            return self._plugin_data

        if self.plugin_meta is None:
            return None

        try:
            self._plugin_data = PluginDataApi.get_cached_data_by_plugin(plugin=self.plugin_meta)
        except PluginDataApi.DoesNotExist:
            logger.warning(
                "%s.plugin_data() PluginDataApi object does not exist for %s %s",
                self.formatted_class_name,
                self.kind,
                self.plugin_meta.name,
            )
        return self._plugin_data

    def plugin_sql_spec_orm2pydantic(self) -> Optional[SAMApiPluginSpec]:
        """
        Convert the api plugin specification from the Django ORM model format to the Pydantic manifest format.

        This method constructs a `SAMPluginStaticSpec` Pydantic model using the prompt, selector,
        and api data associated with the current `plugin_meta`. It retrieves each component
        using their respective ORM-to-Pydantic conversion methods.

        :return: The api plugin specification as a Pydantic model.
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
        self._sql_plugin_spec = SAMApiPluginSpec(
            selector=selector,
            prompt=prompt,
            connection=(
                self.plugin_data.connection.name
                if self.plugin_data and self.plugin_data.connection
                else "missing connection"
            ),
            apiData=data,
        )
        return self._sql_plugin_spec

    def plugin_data_orm2pydantic(self) -> Optional[ApiData]:
        """
        Overrides the parent method to map API plugin data from ORM to Pydantic.
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
        orm_parameters = self.plugin_data.parameters if self.plugin_data else []
        if not isinstance(orm_parameters, list):
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} plugin_data_orm2pydantic() expected parameters to be a list for {self.kind} {self.plugin_meta.name}",
                thing=self.kind,
            )
        for parameter in orm_parameters:
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
        url_params: list[UrlParam] = []
        headers: list[RequestHeader] = []
        self._api_data = ApiData(
            endpoint=self.plugin_data.endpoint if self.plugin_data else "missing endpoint",
            method=self.plugin_data.method if self.plugin_data else "GET",
            urlParams=url_params,
            headers=headers,
            body=self.plugin_data.body if self.plugin_data else None,
            parameters=parameters,
            testValues=test_values,
            limit=10,
        )
        return self._api_data

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def example_manifest(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return a JSON response containing an example API plugin manifest.

        This method generates a sample manifest for an API plugin, including all required fields and example values. The manifest is returned as a structured JSON response, which can be used for documentation, testing, or as a template for new plugin configurations.

        :param request: Django HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments to customize the example manifest.
        :return: JSON response with the example manifest.
        :rtype: SmarterJournaledJsonResponse

        .. seealso::

            :class:`ApiPlugin`
            :meth:`ApiPlugin.example_manifest`
            :class:`SmarterJournaledJsonResponse`

        **Example usage**::

            response = broker.example_manifest(request)
            print(response.data)

        """
        logger.debug(
            "%s.example_manifest() called for %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            args,
            kwargs,
        )
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)
        data = ApiPlugin.example_manifest(kwargs=kwargs)
        return self.json_response_ok(command=command, data=data)

    def describe(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return a JSON response containing the manifest data for the current API plugin.

        This method serializes the plugin manifest, metadata, specification, and status into a structured JSON response. It validates the plugin and its associated data, raising an error if any required component is missing or uninitialized.

        :param request: Django HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: JSON response with manifest data.
        :rtype: SmarterJournaledJsonResponse

        :raises SAMBrokerErrorNotReady:
            If the plugin is not initialized.

        :raises SAMPluginBrokerError:
            If plugin data, account, or plugin metadata is missing, or if serialization fails.

        .. error::
            Any exception during serialization or validation is wrapped and raised as :class:`SAMPluginBrokerError`.

        .. seealso::

            :class:`SAMApiPlugin`
            :class:`ApiPlugin`
            :class:`PluginDataApi`
            :class:`PluginMeta`
            :class:`SmarterJournaledJsonResponse`

        **Example usage**::

            response = broker.describe(request)
            print(response.data)

        .. tip::
            Use this method to inspect the current manifest and plugin details for debugging, API responses, or documentation.

        """
        logger.debug(
            "%s.describe() called for %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            args,
            kwargs,
        )
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)

        if not self.manifest:
            raise SAMBrokerErrorNotReady(message="No manifest found", thing=self.kind, command=command)

        model = json.loads(self.manifest.model_dump_json())
        return self.json_response_ok(command=command, data=model)

    def apply(self, request: "HttpRequest", *args, **kwargs: dict) -> SmarterJournaledJsonResponse:
        """
        Apply the manifest by copying its data to the Django ORM model and saving it to the database.

        This method ensures the manifest is loaded and validated (via `super().apply`) before updating the database. It creates or updates the plugin and its metadata, and saves changes if the plugin is ready. Errors during creation or saving are returned in the response.

        :param request: Django HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments containing manifest data.
        :type kwargs: dict
        :return: JSON response indicating success or error.
        :rtype: SmarterJournaledJsonResponse

        :raises SAMBrokerError:
            If the plugin or plugin metadata is not initialized.

        :raises SAMBrokerErrorNotReady:
            If the plugin is not ready for saving.

        .. error::
            Any exception during creation or saving is returned in the error response.

        .. seealso::

            :meth:`SAMPluginBaseBroker.apply`
            :class:`ApiPlugin`
            :class:`PluginMeta`
            :class:`SmarterJournaledJsonResponse`
            :class:`SAMBrokerError`
            :class:`SAMBrokerErrorNotReady`
            :class:`SAMPluginBaseBroker`
            :class:`SmarterJournalCliCommands``

        **Example usage**::

            response = broker.apply(request, manifest_data=manifest_dict)
            print(response.data)

        .. tip::
            Use this method to onboard, update, or synchronize plugin manifests with the database.

        """
        logger.debug(
            "%s.apply() called for %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            args,
            kwargs,
        )
        super().apply(request, kwargs)
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)

        if not self.user.is_staff:
            raise SAMPluginBrokerError(
                message="Only account admins can apply api plugin manifests.",
                thing=self.kind,
                command=command,
            )

        if self.plugin is None:
            raise SAMBrokerError(
                f"{self.formatted_class_name} plugin not initialized. Cannot apply manifest.",
                thing=self.kind,
                command=command,
            )
        if self.plugin_meta is None:
            raise SAMBrokerError(
                f"{self.formatted_class_name} plugin_meta not initialized. Cannot apply manifest.",
                thing=self.kind,
                command=command,
            )
        try:
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
                f"{self.formatted_class_name} {self.plugin_meta.name} not ready", thing=self.kind, command=command
            )
        except SAMBrokerErrorNotReady as err:
            return self.json_response_err(command=command, e=err)

    def chat(self, request: "HttpRequest", *args, **kwargs: dict) -> SmarterJournaledJsonResponse:
        """
        Handle chat interactions with the API plugin.
        This is not implemented for this class of Broker.

        :raises SAMBrokerErrorNotImplemented:
            Always raised to indicate that this method is not implemented.

        :param request: Django HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: Not implemented error response.
        :rtype: SmarterJournaledJsonResponse
        """
        logger.debug(
            "%s.chat() called for %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            args,
            kwargs,
        )
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="chat() not implemented", thing=self.kind, command=command)

    def delete(self, request: "HttpRequest", *args, **kwargs: dict) -> SmarterJournaledJsonResponse:
        """
        Delete the API plugin associated with this broker and return a JSON response indicating the result.

        This method attempts to delete the plugin and its metadata from the database. If the plugin or its metadata is not initialized, or if the plugin is not ready, an appropriate error is raised. On successful deletion, an empty JSON response is returned.

        :param request: Django HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: JSON response indicating deletion success or error.
        :rtype: SmarterJournaledJsonResponse

        :raises SAMBrokerError:
            If the plugin or plugin metadata is not initialized, or if deletion fails.

        :raises SAMBrokerErrorNotReady:
            If the plugin is not ready for deletion.

        .. error::
            Any exception during deletion is wrapped and raised as :class:`SAMBrokerError`.

        .. seealso::

            :class:`ApiPlugin`
            :class:`PluginMeta`
            :class:`SmarterJournaledJsonResponse`
            :class:`SAMBrokerError`
            :class:`SAMBrokerErrorNotReady`

        **Example usage**::

            response = broker.delete(request, name="my_plugin")
            print(response.data)

        """
        logger.debug(
            "%s.delete() called for %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            args,
            kwargs,
        )
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)

        if not self.user.is_staff:
            raise SAMPluginBrokerError(
                message="Only account admins can delete api plugin manifests.",
                thing=self.kind,
                command=command,
            )

        self.set_and_verify_name_param(command=command)
        if self.plugin is None:
            raise SAMBrokerError(
                f"{self.formatted_class_name} plugin not initialized. Cannot delete.",
                thing=self.kind,
                command=command,
            )
        if self.plugin_meta is None:
            raise SAMBrokerError(
                f"{self.formatted_class_name} plugin_meta not initialized. Cannot delete.",
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

    def deploy(self, request: "HttpRequest", *args, **kwargs: dict) -> SmarterJournaledJsonResponse:
        """
        Deploy the API plugin.
        This is not implemented for this class of Broker.

        :raises SAMBrokerErrorNotImplemented:
            Always raised to indicate that this method is not implemented.

        :param request: Django HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: Not implemented error response.
        :rtype: SmarterJournaledJsonResponse
        """
        logger.debug(
            "%s.deploy() called for %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            args,
            kwargs,
        )
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("deploy() not implemented", thing=self.kind, command=command)

    def undeploy(self, request: "HttpRequest", *args, **kwargs: dict) -> SmarterJournaledJsonResponse:
        """
        Undeploy the API plugin.
        This is not implemented for this class of Broker.

        :raises SAMBrokerErrorNotImplemented:
            Always raised to indicate that this method is not implemented.

        :param request: Django HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: Not implemented error response.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("undeploy() not implemented", thing=self.kind, command=command)

    def logs(self, request: "HttpRequest", *args, **kwargs: dict) -> SmarterJournaledJsonResponse:
        """
        Retrieve logs for the API plugin.
        This is not implemented for this class of Broker.

        :raises SAMBrokerErrorNotImplemented:
            Always raised to indicate that this method is not implemented.

        :param request: Django HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: Not implemented error response.
        :rtype: SmarterJournaledJsonResponse
        """
        logger.debug(
            "%s.logs() called for %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            args,
            kwargs,
        )
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("logs() not implemented", thing=self.kind, command=command)
