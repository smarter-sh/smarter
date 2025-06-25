# pylint: disable=W0718
"""Smarter API SqlPlugin Manifest handler"""

import logging
from typing import Optional, Type

from django.forms.models import model_to_dict
from django.http import HttpRequest

from smarter.apps.plugin.manifest.enum import (
    SAMPluginSpecKeys,
    SAMSqlPluginSpecDataKeys,
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
from smarter.apps.plugin.manifest.models.sql_plugin.const import MANIFEST_KIND
from smarter.apps.plugin.manifest.models.sql_plugin.enum import SAMSqlPluginSpecSqlData
from smarter.apps.plugin.manifest.models.sql_plugin.model import SAMSqlPlugin
from smarter.apps.plugin.manifest.models.sql_plugin.spec import (
    SAMSqlPluginSpec,
    SqlData,
)
from smarter.apps.plugin.models import (
    PluginDataSql,
    PluginMeta,
    PluginPrompt,
    PluginSelector,
)
from smarter.apps.plugin.plugin.sql import SqlPlugin
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
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


logger = logging.getLogger(__name__)


class SAMSqlPluginBroker(SAMPluginBaseBroker):
    """
    Smarter API Plugin Manifest Broker.This class is responsible for
    - loading, validating and parsing the Smarter Sql yaml Plugin manifests
    - using the manifest to initialize the corresponding Pydantic model

    The Plugin object provides the generic services for the Plugin, such as
    instantiation, create, update, delete, etc.
    """

    # override the base abstract manifest model with the Plugin model
    _manifest: Optional[SAMSqlPlugin] = None
    _pydantic_model: Type[SAMSqlPlugin] = SAMSqlPlugin
    _plugin: Optional[SqlPlugin] = None
    _plugin_meta: Optional[PluginMeta] = None
    _plugin_data: Optional[PluginDataSql] = None

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def formatted_class_name(self) -> str:
        """
        Returns the formatted class name for logging purposes.
        This is used to provide a more readable class name in logs.
        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.SAMSqlPluginBroker()"

    @property
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMSqlPlugin]:
        """
        SAMSqlPlugin() is a Pydantic model
        that is used to represent the Smarter API Plugin manifest. The Pydantic
        model is initialized with the data from the manifest loader, which is
        generally passed to the model constructor as **data. However, this top-level
        manifest model has to be explicitly initialized, whereas its child models
        are automatically cascade-initialized by the Pydantic model, implicitly
        passing **data to each child's constructor.
        """
        if self._manifest:
            return self._manifest
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

    @property
    def plugin(self) -> Optional[SqlPlugin]:
        if self._plugin:
            return self._plugin
        if isinstance(self.plugin_meta, PluginMeta):
            self._plugin = SqlPlugin(
                plugin_meta=self.plugin_meta,
                user_profile=self.user_profile,
            )
        elif isinstance(self.manifest, SAMSqlPlugin):
            self._plugin = SqlPlugin(
                user_profile=self.user_profile,
                manifest=self.manifest,
            )
        return self._plugin

    @property
    def plugin_data(self) -> Optional[PluginDataSql]:
        """
        Returns the PluginDataStatic object for this broker.
        This is used to store the plugin data in the database.
        """
        if self._plugin_data:
            return self._plugin_data

        if self.plugin_meta is None:
            return None

        try:
            self._plugin_data = PluginDataSql.objects.get(plugin=self.plugin_meta)
        except PluginDataSql.DoesNotExist:
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
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)
        data = SqlPlugin.example_manifest(kwargs=kwargs)
        return self.json_response_ok(command=command, data=data)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return a JSON response with the manifest data."""
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)

        if not isinstance(self.plugin, SqlPlugin):
            raise SAMBrokerErrorNotReady(message="No plugin found", thing=self.kind, command=command)
        if not self.plugin_data:
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} {self.kind} plugin_data not initialized. Cannot describe",
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
            logger.info(
                "%s.describe() PluginMeta %s %s",
                self.formatted_class_name,
                self.kind,
                metadata,
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
            logger.info(
                "%s.describe() PluginSelector %s %s",
                self.formatted_class_name,
                self.kind,
                plugin_selector,
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
            logger.info(
                "%s.describe() PluginPrompt %s %s",
                self.formatted_class_name,
                self.kind,
                plugin_prompt,
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

            # pylint: disable=W0105
            """
            before transform, ['parameters']['properties'] is a dict of dicts
                {
                    'id': 4171,
                    'plugin': 4519,
                    'description': 'This SQL query retrieves the Django user record for the username provided.\n',
                    'parameters': {
                        'type': 'object',
                        'required': ['username'],
                        'properties': {
                            'unit': {'enum': ['Celsius', 'Fahrenheit'], 'type': 'string', 'description': 'The temperature unit to use.'},
                            'username': {'type': 'string', 'description': 'The username to query.'}
                            },
                        'additionalProperties': False
                    },
                    'plugindatabasePtr': 4171,
                    'connection': 955,
                    'sqlQuery': "SELECT * FROM auth_user WHERE username = '{username}';\n",
                    'testValues': [{'name': 'username', 'value': 'admin'}, {'name': 'unit', 'value': 'Celsius'}],
                    'limit': 10
                }

                after transform, ['parameters']['properties'] becomes a list of dicts where each dict has a 'name' key
                and the value is the original dict, e.g., and, the requirements list is re-merged into the properties dicts
                as the 'required' key (true, false) in each dict:

                {
                'id': 4171,
                'plugin': 4519,
                'description': 'This SQL query retrieves the Django user record for the username provided.\n',
                'parameters': [
                    {
                        'name': 'unit',
                        'enum': ['Celsius', 'Fahrenheit'],
                        'type': 'string',
                        'required': false
                        'description': 'The temperature unit to use.'
                    },
                    {
                        'name': 'username',
                        'type': 'string',
                        'required': true
                        'description': 'The username to query.'
                    }
                ],
                'plugindatabasePtr': 4171,
                'connection': 955,
                'sqlQuery': "SELECT * FROM auth_user WHERE username = '{username}';\n",
                'testValues': [{'name': 'username', 'value': 'admin'}, {'name': 'unit', 'value': 'Celsius'}],
                'limit': 10
                }
            """
            if SAMSqlPluginSpecSqlData.PARAMETERS.value in plugin_data:
                parameters = plugin_data[SAMSqlPluginSpecSqlData.PARAMETERS.value]
                if (
                    isinstance(parameters, dict)
                    and "properties" in parameters
                    and isinstance(parameters["properties"], dict)
                ):
                    properties_dict = parameters["properties"]
                    required_list = parameters.get("required", [])
                    # Convert dict of dicts to list of dicts with 'name' and 'required' keys
                    properties_list = []
                    for k, v in properties_dict.items():
                        prop = {"name": k, **v}
                        prop["required"] = k in required_list
                        properties_list.append(prop)
                    plugin_data[SAMSqlPluginSpecSqlData.PARAMETERS.value] = properties_list

            plugin_data = SqlData(**plugin_data)
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
                    SAMPluginSpecKeys.CONNECTION.value: (
                        self.plugin_data.connection.name if self.plugin_data.connection else ""
                    ),
                    SAMPluginSpecKeys.SQL_DATA.value: plugin_data.model_dump(),
                },
                SAMKeys.STATUS.value: {
                    "created": self.plugin_meta.created_at.isoformat(),
                    "modified": self.plugin_meta.updated_at.isoformat(),
                },
            }

            logger.info(
                "%s.describe() returning %s %s",
                self.formatted_class_name,
                self.kind,
                retval,
            )

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
                model_dump = PluginSerializer(plugin).data
                if not model_dump:
                    raise SAMPluginBrokerError(
                        f"Model dump failed for {self.kind} {plugin.name}", thing=self.kind, command=command
                    )

                # round-trip the model dump through the Pydantic model to ensure that
                # it is valid and to serialize it to JSON
                pydantic_model = self.pydantic_model(**model_dump)
                model_dump = pydantic_model.model_dump_json()

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
        apply the manifest. copy the manifest data to the Django ORM model and
        save the model to the database. Call super().apply() to ensure that the
        manifest is loaded and validated before applying the manifest to the
        Django ORM model.
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
            return self.json_response_ok(command=command, data={})
        try:
            raise SAMBrokerErrorNotReady(
                f"{self.formatted_class_name} {self.plugin_meta.name if self.plugin_meta else self.kind or "SqlPlugin"} not ready",
                thing=self.kind,
                command=command,
            )
        except SAMBrokerErrorNotReady as err:
            return self.json_response_err(command=command, e=err)

    def chat(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="chat() not implemented", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
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
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("deploy() not implemented", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("undeploy() not implemented", thing=self.kind, command=command)

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("logs() not implemented", thing=self.kind, command=command)
