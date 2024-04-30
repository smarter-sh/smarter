"""Smarter API Plugin Manifest handler"""

from smarter.apps.api.v0.manifests.broker import SAMBroker

from .models.plugin import SAMPlugin


class SAMPluginBroker(SAMBroker):
    """
    Smarter API Plugin Manifest Broker.This class is responsible
    for loading, validating and parsing the Smarter Api yaml Plugin manifests and then
    using these to initialize the corresponding Pydantic models.
    """

    _manifest: SAMPlugin = None

    def __init__(
        self,
        manifest: str = None,
        file_path: str = None,
        url: str = None,
    ):
        # load, validate and parse the manifest
        super().__init__(manifest=manifest, file_path=file_path, url=url)

        # initialize the Plugin manifest model
        self._manifest = SAMPlugin(**self.loader.data)

    @property
    def manifest(self) -> SAMPlugin:
        return self._manifest
