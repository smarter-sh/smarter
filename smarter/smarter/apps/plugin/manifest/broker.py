# pylint: disable=W0718
"""Smarter API Plugin Manifest handler"""

from django.http import HttpRequest, JsonResponse

from smarter.apps.account.account_mixin import AccountMixin
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.manifest.models.plugin import SAMPlugin
from smarter.apps.plugin.plugin.base import PluginBase
from smarter.lib.manifest.broker import AbstractBroker

from .const import MANIFEST_KIND


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

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        api_version: str,
        account_number: str,
        kind: str = None,
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
            account_number=account_number,
            kind=kind,
            manifest=manifest,
            file_path=file_path,
            url=url,
        )

    @property
    def plugin(self) -> PluginBase:
        """
        PluginController() is a helper class to map the manifest model
        metadata.pluginClass to an instance of the the correct plugin class.
        """
        if self._plugin:
            return self._plugin
        controller = PluginController(self.manifest)
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
    def get(self, request: HttpRequest = None) -> JsonResponse:
        if self.plugin.ready:
            try:
                data = self.plugin.to_json()
                return self.success_response(data)
            except Exception as e:
                return self.err_response(self.get.__name__, e)
        return self.not_ready_response()

    def apply(self, request: HttpRequest = None) -> JsonResponse:
        try:
            self.plugin.create()
        except Exception as e:
            return self.err_response("create", e)

        if self.plugin.ready:
            try:
                self.plugin.save()
                return self.success_response(data={})
            except Exception as e:
                return self.err_response(self.apply.__name__, e)
        return self.not_ready_response()

    def describe(self, request: HttpRequest = None) -> JsonResponse:
        if self.plugin.ready:
            try:
                data = self.plugin.to_json()
                return self.success_response(data)
            except Exception as e:
                return self.err_response(self.describe.__name__, e)
        return self.not_ready_response()

    def delete(self, request: HttpRequest = None) -> JsonResponse:
        if self.plugin.ready:
            try:
                self.plugin.delete()
                return self.success_response(data={})
            except Exception as e:
                return self.err_response(self.delete.__name__, e)
        return self.not_ready_response()

    def deploy(self, request: HttpRequest = None) -> JsonResponse:
        return self.not_implemented_response()

    def logs(self, request: HttpRequest = None) -> JsonResponse:
        return self.not_implemented_response()
