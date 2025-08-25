# pylint: disable=W0718
"""Smarter API ApiPlugin Manifest handler"""

import logging
from typing import Optional, Type

from django.http import HttpRequest

from smarter.apps.plugin.manifest.enum import SAMPluginSpecKeys
from smarter.apps.plugin.manifest.models.api_plugin.const import MANIFEST_KIND
from smarter.apps.plugin.manifest.models.api_plugin.model import SAMApiPlugin
from smarter.apps.plugin.manifest.models.api_plugin.spec import ApiData
from smarter.apps.plugin.models import PluginDataApi, PluginMeta
from smarter.apps.plugin.plugin.api import ApiPlugin
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

from ..models.api_plugin.spec import SAMApiPluginSpec
from ..models.common.plugin.metadata import SAMPluginCommonMetadata
from . import PluginSerializer, SAMPluginBrokerError
from .plugin_base import SAMPluginBaseBroker


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)
        and waffle.switch_is_active(SmarterWaffleSwitches.MANIFEST_LOGGING)
    ) and level >= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class SAMApiPluginBroker(SAMPluginBaseBroker):
    """
    Smarter API ApiPlugin Manifest Broker.This class is responsible for
    - loading, validating and parsing the Smarter Api yaml ApiPlugin manifests
    - using the manifest to initialize the corresponding Pydantic model

    The ApiPlugin object provides the generic services for the ApiPlugin, such as
    instantiation, create, update, delete, etc.
    """

    # override the base abstract manifest model with the ApiPlugin model
    _plugin: Optional[ApiPlugin] = None
    _plugin_data: Optional[PluginDataApi] = None
    _manifest: Optional[SAMApiPlugin] = None
    _pydantic_model: Type[SAMApiPlugin] = SAMApiPlugin
    _plugin_meta: Optional[PluginMeta] = None

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
        return f"{parent_class}.SAMApiPluginBroker()"

    @property
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMApiPlugin]:
        """
        SAMApiPlugin() is a Pydantic model
        that is used to represent the Smarter API ApiPlugin manifest. The Pydantic
        model is initialized with the data from the manifest loader, which is
        generally passed to the model constructor as **data. However, this top-level
        manifest model has to be explicitly initialized, whereas its child models
        are automatically cascade-initialized by the Pydantic model, implicitly
        passing **data to each child's constructor.
        """
        if self._manifest:
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMApiPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMApiPluginSpec(**self.loader.manifest_spec),
            )
        return self._manifest

    @property
    def plugin(self) -> Optional[ApiPlugin]:
        if self._plugin:
            return self._plugin
        self._plugin = ApiPlugin(
            plugin_meta=self.plugin_meta,
            user_profile=self.user_profile,
            manifest=self.manifest,
            name=self.name,
        )
        return self._plugin

    @property
    def plugin_data(self) -> Optional[PluginDataApi]:
        """
        Returns the PluginDataStatic object for this broker.
        This is used to store the plugin data in the database.
        """
        if self._plugin_data:
            return self._plugin_data

        if self.plugin_meta is None:
            return None

        try:
            self._plugin_data = PluginDataApi.objects.get(plugin=self.plugin_meta)
        except PluginDataApi.DoesNotExist:
            logger.warning(
                "%s.plugin_data() PluginDataApi object does not exist for %s %s",
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
        data = ApiPlugin.example_manifest(kwargs=kwargs)
        return self.json_response_ok(command=command, data=data)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return a JSON response with the manifest data."""
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)

        if not isinstance(self.plugin, ApiPlugin):
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

        metadata = self.plugin_metadata_orm2pydantic()
        plugin_selector = self.plugin_selector_orm2pydantic()
        plugin_prompt = self.plugin_prompt_orm2pydantic()

        try:
            plugin_data = self.plugin_data_orm2pydantic()
            plugin_data = ApiData(**plugin_data)
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
                    SAMPluginSpecKeys.API_DATA.value: plugin_data.model_dump(),
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
                "%s.describe() failed to serialize %s %s: %s",
                self.formatted_class_name,
                self.kind,
                self.plugin.name,
                str(e),
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
            chatbots = PluginMeta.objects.filter(account=self.account, name=name)
        else:
            chatbots = PluginMeta.objects.filter(account=self.account)
        logger.info(
            "%s.get() found %s ApiPlugins for account %s", self.formatted_class_name, chatbots.count(), self.account
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
                if not isinstance(camel_cased_model_dump, dict):
                    raise SAMPluginBrokerError(
                        f"Invalid model dump for {self.kind} {chatbot.name}: {camel_cased_model_dump}",
                        thing=self.kind,
                        command=command,
                    )

                # round-trip the model dump through the Pydantic model to ensure that
                # it is valid and to convert it to a JSON string
                pydantic_model = self.pydantic_model(**camel_cased_model_dump)
                camel_cased_model_dump = pydantic_model.model_dump_json()

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

    def apply(self, request: HttpRequest, *args, **kwargs: dict) -> SmarterJournaledJsonResponse:
        """
        apply the manifest. copy the manifest data to the Django ORM model and
        save the model to the database. Call super().apply() to ensure that the
        manifest is loaded and validated before applying the manifest to the
        Django ORM model.
        """
        super().apply(request, kwargs)
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)
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

    def chat(self, request: HttpRequest, *args, **kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="chat() not implemented", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, *args, **kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
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

    def deploy(self, request: HttpRequest, *args, **kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("deploy() not implemented", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, *args, **kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("undeploy() not implemented", thing=self.kind, command=command)

    def logs(self, request: HttpRequest, *args, **kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("logs() not implemented", thing=self.kind, command=command)
