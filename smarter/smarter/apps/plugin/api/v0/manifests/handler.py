"""Smarter API Plugin Manifest handler"""

from smarter.apps.api.v0.manifests.handler import SAMHandler

from .models.plugin import SAMPlugin, SAMPluginMetadata, SAMPluginSpec, SAMPluginStatus


class SAMPluginHandler(SAMHandler):
    """
    Smarter API Plugin Manifest Handler. This class is responsible
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

        metadata_dict = self.loader.manifest_metadata()
        metadata = SAMPluginMetadata(**metadata_dict)

        spec_dict = self.loader.manifest_spec()
        spec = SAMPluginSpec(**spec_dict)

        status_dict = self.loader.manifest_status()
        status = SAMPluginStatus(**status_dict)

        self._manifest = SAMPlugin(metadata=metadata, spec=spec, status=status)

    @property
    def manifest(self) -> SAMPlugin:
        return self._manifest
