# pylint: disable=W0718
"""Smarter API Plugin Manifest handler"""

from django.http import HttpRequest
from taggit.models import Tag

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.models import Account
from smarter.apps.plugin.manifest.enum import SAMPluginMetadataClassValues
from smarter.apps.plugin.plugin.base import PluginBase
from smarter.apps.plugin.plugin.sql import PluginSql
from smarter.apps.plugin.plugin.static import PluginStatic
from smarter.common.api import SmarterApiVersions
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import (
    AbstractBroker,
    SAMBrokerError,
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
)
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
    SCLIResponseGetData,
)
from smarter.lib.manifest.loader import SAMLoader

from ...models import PluginMeta
from ...plugin.base import PluginBase
from ..controller import PluginController
from ..models.plugin.const import MANIFEST_KIND
from ..models.plugin.model import SAMPlugin


MAX_RESULTS = 1000

PluginMap: dict[str, PluginBase] = {
    SAMPluginMetadataClassValues.STATIC.value: PluginStatic,
    SAMPluginMetadataClassValues.SQL.value: PluginSql,
}


class SAMPluginBrokerError(SAMBrokerError):
    """Base exception for Smarter API Plugin Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Plugin Manifest Broker Error"


class SAMPluginBroker(AbstractBroker, AccountMixin):
    """
    Smarter API Plugin Manifest Broker.This class is responsible for
    - loading, validating and parsing the Smarter Api yaml Plugin manifests
    - using the manifest to initialize the corresponding Pydantic model

    The Plugin object provides the generic services for the Plugin, such as
    instantiation, create, update, delete, etc.
    """

    # override the base abstract manifest model with the Plugin model
    _manifest: SAMPlugin = None
    _plugin: PluginBase = None
    _plugin_meta: PluginMeta = None

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        request: HttpRequest,
        account: Account,
        api_version: str = SmarterApiVersions.V1.value,
        name: str = None,
        kind: str = None,
        loader: SAMLoader = None,
        manifest: str = None,
        file_path: str = None,
        url: str = None,
    ):
        """
        Load, validate and parse the manifest. The parent will initialize
        the generic manifest loader class, SAMLoader(), which can then be used to
        provide initialization data to any kind of manifest model. the loader
        also performs cursory high-level validation of the manifest, sufficient
        to ensure that the manifest is a valid yaml file and that it contains
        the required top-level keys.
        """
        super().__init__(
            request=request,
            account=account,
            api_version=api_version,
            name=name,
            kind=kind,
            loader=loader,
            manifest=manifest,
            file_path=file_path,
            url=url,
        )

    @property
    def plugin_meta(self) -> PluginMeta:
        if self._plugin_meta:
            return self._plugin_meta
        if self.name and self.account:
            try:
                self._plugin_meta = PluginMeta.objects.get(account=self.account, name=self.name)
            except PluginMeta.DoesNotExist:
                pass
        return self._plugin_meta

    @property
    def plugin(self) -> PluginBase:
        """
        PluginController() is a helper class to map the manifest model
        metadata.pluginClass to an instance of the the correct plugin class.
        """
        if self._plugin:
            return self._plugin
        controller = PluginController(account=self.account, manifest=self.manifest, plugin_meta=self.plugin_meta)
        self._plugin = controller.obj
        return self._plugin

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> SAMPlugin:
        """
        SAMPlugin() is a Pydantic model
        that is used to represent the Smarter API Plugin manifest. The Pydantic
        model is initialized with the data from the manifest loader, which is
        generally passed to the model constructor as **data. However, this top-level
        manifest model has to be explicitly initialized, whereas its child models
        are automatically cascade-initialized by the Pydantic model, implicitly
        passing **data to each child's constructor.
        """
        if self._manifest:
            return self._manifest
        if self.loader:
            self._manifest = SAMPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=self.loader.manifest_metadata,
                spec=self.loader.manifest_spec,
                status=self.loader.manifest_status,
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def example_manifest(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)
        plugin_class: str = self.params.get("plugin_class", SAMPluginMetadataClassValues.STATIC.value)
        try:
            Plugin = PluginMap[plugin_class]
        except KeyError as e:
            raise SAMPluginBrokerError(
                f"Plugin class {plugin_class} not found", thing=self.kind, command=command
            ) from e

        data = Plugin.example_manifest(kwargs=kwargs)
        return self.json_response_ok(command=command, data=data)

    # pylint: disable=W0221
    def get_model_titles(self) -> list[dict[str, str]]:
        titles = [
            {"name": f, "type": str(t)}
            for f, t in self.plugin.manifest.__annotations__.items()
            if f != "class_identifier"
        ]
        return titles

    def get(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        name: str = self.params.get("name", None)
        all_objects: bool = self.params.get("all_objects", False)
        tags: str = self.params.get("tags", None)
        data = []

        # generate a QuerySet of PluginMeta objects that match our search criteria
        if name:
            plugins = PluginMeta.objects.filter(account=self.account, name=name)
        else:
            if all_objects:
                plugins = PluginMeta.objects.filter(account=self.account)
            else:
                if tags:
                    tags = Tag.objects.filter(name__in=tags)
                    plugins = PluginMeta.objects.filter(account=self.account, tags__in=tags)[:MAX_RESULTS]
                else:
                    plugins = PluginMeta.objects.filter(account=self.account)[:MAX_RESULTS]

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each Plugin
        for plugin_meta in plugins:
            controller = PluginController(account=self.account, plugin_meta=plugin_meta)
            try:
                model_titles = controller.get_model_titles()
                model_dump = controller.model_dump_json()
                if not model_dump:
                    raise SAMBrokerError(
                        f"Plugin {plugin_meta.name} model dump failed", thing=self.kind, command=command
                    )
                data.append(model_dump)
            except Exception as e:
                raise SAMBrokerError(
                    f"Plugin {plugin_meta.name} model dump failed", thing=self.kind, command=command
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: name,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: self.params,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: model_titles,
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        """
        apply the manifest. copy the manifest data to the Django ORM model and
        save the model to the database. Call super().apply() to ensure that the
        manifest is loaded and validated before applying the manifest to the
        Django ORM model.
        """
        super().apply(request, kwargs)
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)
        try:
            self.plugin.create()
        except Exception as e:
            raise SAMBrokerError(
                f"Plugin {self.plugin_meta.name} create failed", thing=self.kind, command=command
            ) from e

        if self.plugin.ready:
            try:
                self.plugin.save()
            except Exception as e:
                raise SAMBrokerError(
                    f"Plugin {self.plugin_meta.name} save failed", thing=self.kind, command=command
                ) from e
            return self.json_response_ok(command=command, data={})
        raise SAMBrokerErrorNotReady(f"Plugin {self.plugin_meta.name} not ready", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        self.set_and_verify_name_param(command=command)
        if self.plugin.ready:
            try:
                data = self.plugin.to_json()
                data["metadata"].pop("account")
                data["metadata"].pop("author")
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                raise SAMBrokerError(
                    f"Plugin {self.plugin_meta.name} describe failed", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"Plugin {self.plugin_meta.name} not ready", thing=self.kind, command=command)

    def chat(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="chat() not implemented", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        self.set_and_verify_name_param(command=command)
        if self.plugin.ready:
            try:
                self.plugin.delete()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                raise SAMBrokerError(
                    f"Plugin {self.plugin_meta.name} delete failed", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"Plugin {self.plugin_meta.name} not ready", thing=self.kind, command=command)

    def deploy(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("deploy() not implemented", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("undeploy() not implemented", thing=self.kind, command=command)

    def logs(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("logs() not implemented", thing=self.kind, command=command)
