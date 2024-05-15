# pylint: disable=W0718
"""Smarter API Plugin Manifest handler"""

from django.http import HttpRequest, JsonResponse
from taggit.models import Tag

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.models import Account
from smarter.lib.manifest.broker import AbstractBroker
from smarter.lib.manifest.exceptions import SAMExceptionBase
from smarter.lib.manifest.loader import SAMLoader

from ..manifest.controller import PluginController
from ..manifest.models.plugin.model import SAMPlugin
from ..models import PluginMeta
from ..plugin.base import PluginBase
from .models.plugin.const import MANIFEST_KIND


MAX_RESULTS = 1000


class SAMPluginBrokerError(SAMExceptionBase):
    """Base exception for Smarter API Plugin Broker handling."""


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
        api_version: str,
        account: Account,
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
            api_version=api_version,
            account=account,
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
        print("plugin() -  self.plugin_meta", self.plugin_meta)
        print("account", self.account)
        print("name", self.name)
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
    def get(
        self, request: HttpRequest = None, name: str = None, all_objects: bool = False, tags: str = None
    ) -> JsonResponse:

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

        if not plugins.exists():
            return self.not_found_response()

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each Plugin
        for plugin_meta in plugins:
            controller = PluginController(account=self.account, plugin_meta=plugin_meta)
            try:
                model_dump = controller.model_dump_json()
                if not model_dump:
                    raise SAMPluginBrokerError(f"Model dump failed for {self.kind} {plugin_meta.name}")
                data.append(model_dump)
            except Exception as e:
                return self.err_response(self.get.__name__, e)
        data = {
            "apiVersion": self.api_version,
            "kind": self.kind,
            "name": name,
            "all_objects": all_objects,
            "tags": tags,
            "metadata": {"count": len(data)},
            "items": data,
        }
        return self.success_response(operation=self.get.__name__, data=data)

    def apply(self, request: HttpRequest = None) -> JsonResponse:
        try:
            self.plugin.create()
        except Exception as e:
            return self.err_response("create", e)

        if self.plugin.ready:
            try:
                self.plugin.save()
                return self.success_response(operation=self.apply.__name__, data={})
            except Exception as e:
                return self.err_response(self.apply.__name__, e)
        return self.not_ready_response()

    def describe(self, request: HttpRequest = None) -> JsonResponse:
        if self.plugin.ready:
            try:
                data = self.plugin.to_json()
                return self.success_response(operation=self.describe.__name__, data=data)
            except Exception as e:
                return self.err_response(self.describe.__name__, e)
        return self.not_ready_response()

    def delete(self, request: HttpRequest = None) -> JsonResponse:
        if self.plugin.ready:
            try:
                self.plugin.delete()
                return self.success_response(operation=self.delete.__name__, data={})
            except Exception as e:
                return self.err_response(self.delete.__name__, e)
        return self.not_ready_response()

    def deploy(self, request: HttpRequest = None) -> JsonResponse:
        return self.not_implemented_response()

    def logs(self, request: HttpRequest = None) -> JsonResponse:
        return self.not_implemented_response()
