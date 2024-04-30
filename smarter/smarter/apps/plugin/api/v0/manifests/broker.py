"""Smarter API Plugin Manifest handler"""

import logging

from smarter.apps.api.v0.manifests.broker import SAMBroker

from .models.plugin import SAMPlugin


logger = logging.getLogger(__name__)


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
        self._manifest = SAMPlugin(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=self.loader.manifest_metadata,
            spec=self.loader.manifest_spec,
            status=self.loader.manifest_status,
        )

    @property
    def manifest(self) -> SAMPlugin:
        return self._manifest
