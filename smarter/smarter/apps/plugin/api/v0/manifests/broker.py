"""Smarter API Plugin Manifest handler"""

from smarter.apps.api.v0.manifests.broker import AbstractBroker
from smarter.apps.plugin.api.v0.manifests.models.plugin import SAMPlugin
from smarter.apps.plugin.controller import PluginController
from smarter.apps.plugin.plugin.base import PluginBase


class SAMPluginBroker(AbstractBroker):
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

    def __init__(
        self,
        account_number: str,
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
        super().__init__(account_number=account_number, manifest=manifest, file_path=file_path, url=url)

    # override the base abstract manifest model with the Plugin model
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

    def get(self) -> dict:
        return self.plugin.to_json()

    def post(self) -> dict:
        self.plugin.create()
        if self.plugin.ready:
            self.plugin.save()
        return self.plugin.to_json()

    def put(self) -> dict:
        self.plugin.update()
        if self.plugin.ready:
            self.plugin.save()
        return self.plugin.to_json()

    def patch(self) -> dict:
        self.plugin.update()
        if self.plugin.ready:
            self.plugin.save()
        return self.plugin.to_json()

    def delete(self) -> dict:
        if self.plugin.ready:
            self.plugin.delete()
        return self.plugin.to_json()
