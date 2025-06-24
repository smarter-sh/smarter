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


class SAMStaticPluginBroker(SAMPluginBaseBroker):
    """
    Smarter API StaticPlugin Manifest Broker.This class is responsible for
    - loading, validating and parsing the Smarter Api yaml StaticPlugin manifests
    - using the manifest to initialize the corresponding Pydantic model

    The StaticPlugin object provides the generic services for the StaticPlugin, such as
    instantiation, create, update, delete, etc.
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
        Returns the formatted class name for logging purposes.
        This is used to provide a more readable class name in logs.
        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.SAMStaticPluginBroker()"

    @property
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMStaticPlugin]:
        """
        SAMStaticPlugin() is a Pydantic model
        that is used to represent the Smarter API StaticPlugin manifest. The Pydantic
        model is initialized with the data from the manifest loader, which is
        generally passed to the model constructor as **data. However, this top-level
        manifest model has to be explicitly initialized, whereas its child models
        are automatically cascade-initialized by the Pydantic model, implicitly
        passing **data to each child's constructor.
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
        if self._plugin:
            return self._plugin
        if isinstance(self.plugin_meta, PluginMeta):
            self._plugin = StaticPlugin(
                plugin_meta=self.plugin_meta,
                user_profile=self.user_profile,
            )
        elif isinstance(self.manifest, SAMStaticPlugin):
            self._plugin = StaticPlugin(
                user_profile=self.user_profile,
                manifest=self.manifest,
            )
        return self._plugin

    @property
    def plugin_data(self) -> Optional[PluginDataStatic]:
        """
        Returns the PluginDataStatic object for this broker.
        This is used to store the plugin data in the database.
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
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)
        data = StaticPlugin.example_manifest(kwargs=kwargs)
        return self.json_response_ok(command=command, data=data)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return a JSON response with the manifest data.
        example response:
        {
            "apiVersion": "smarter.sh/v1",
            "kind": "Plugin",
            "metadata": {
                "name": "cli_test_plugin",
                "description": "A 'hello world' style plugin. This is an example plugin to integrate with OpenAI API Function Calling additional information plugin_data, in this module.",
                "version": "0.2.0",
                "tags": [],
                "annotations": null,
                "pluginClass": "static"
            },
            "spec": {
                "prompt": {
                    "provider": "openai",
                    "systemRole": "Your job is to provide helpful technical information about the OpenAI API Function Calling feature. You should include the following information in your response: \"Congratulations!!! OpenAI API Function Calling chose to call this plugin_data. Here is the additional information that you requested:\"\n",
                    "model": "gpt-4-turbo",
                    "temperature": 0.5,
                    "maxTokens": 256
                },
                "selector": {
                    "directive": "search_terms",
                    "searchTerms": [
                        "Cli Test",
                        "cli test plugin",
                        "test plugin"
                    ]
                },
                "data": {
                    "description": "A 'hello world' style plugin. This is an example plugin to integrate with OpenAI API Function Calling additional information plugin_data, in this module.",
                    "staticData": {
                        "description": "an example plugin to integrate with OpenAI API Function Calling additional information plugin_data, in this module.",
                        "staticData": {
                            "about": "In an API call, you can describe functions and have the model intelligently choose to output a JSON object containing arguments to call one or many functions. The Chat Completions API does not call the plugin_data; instead, the model generates JSON that you can use to call the plugin_data in your code. The latest models (gpt-4-turbo and gpt-4-1106-preview) have been trained to both detect when a plugin_data should to be called (depending on the input) and to respond with JSON that adheres to the plugin_data signature more closely than previous models. With this capability also comes potential risks. We strongly recommend building in user confirmation flows before taking actions that impact the world on behalf of users (sending an email, posting something online, making a purchase, etc).\n",
                            "links": [
                                {
                                    "documentation": "https://platform.openai.com/docs/guides/function-calling"
                                },
                                {
                                    "website": "https://openai.com/"
                                },
                                {
                                    "wikipedia": "https://en.wikipedia.org/wiki/OpenAI"
                                }
                            ],
                            "platformProvider": "OpenAI"
                        }
                    }
                }
            },
            "status": {
                "created": "2025-06-24T21:38:36.368058+00:00",
                "modified": "2025-06-24T21:38:36.434526+00:00"
            }
        }

        """
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)

        if not isinstance(self.plugin, StaticPlugin):
            raise SAMBrokerErrorNotReady(message="No plugin found", thing=self.kind, command=command)
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
            logger.info(
                "%s.describe() PluginDataStatic %s %s",
                self.formatted_class_name,
                self.kind,
                plugin_data,
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
            data = pydantic_model.model_dump_json()
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
        apply the manifest. copy the manifest data to the Django ORM model and
        save the model to the database. Call super().apply() to ensure that the
        manifest is loaded and validated before applying the manifest to the
        Django ORM model.
        """
        super().apply(request, kwargs)
        logger.info("SAMStaticPluginBroker.apply() called %s with args: %s, kwargs: %s", request, args, kwargs)
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
            return self.json_response_ok(command=command, data={})
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
        super().chat(request, kwargs)
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="chat() not implemented", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
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
