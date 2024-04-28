"""Smarter API Manifest Handler base class."""

import logging

from .enum import SAMKeys, SAMMetadataKeys
from .loader import SAMLoader
from .models import SAM, SAMMetadataBase, SAMSpecBase, SAMStatusBase


logger = logging.getLogger(__name__)


###############################################################################
# Handler
###############################################################################
class SAMHandler:
    """
    Smarter API Manifest Handler ("SAMH") base class. This class is responsible
    for loading, validating and parsing the Smarter Api yaml manifests and then
    using these to initialize the corresponding Pydantic models.
    """

    _manifest: SAM = None
    _loader: SAMLoader = None

    def __init__(
        self,
        manifest: str = None,
        file_path: str = None,
        url: str = None,
    ):
        # load, validate and parse the manifest into json
        self._loader = SAMLoader(manifest, file_path, url)

        # initialize Pydantic models from the SAMLoader
        name = self.loader.manifest_metadata(key=SAMMetadataKeys.NAME.value)
        description = self.loader.manifest_metadata(key=SAMMetadataKeys.DESCRIPTION.value)
        version = self.loader.manifest_metadata(key=SAMMetadataKeys.VERSION.value)
        tags = self.loader.manifest_metadata(key=SAMMetadataKeys.TAGS.value)
        annotations = self.loader.manifest_metadata(key=SAMMetadataKeys.ANNOTATIONS.value)

        metadata = SAMMetadataBase(
            name=name, description=description, version=version, tags=tags, annotations=annotations
        )
        spec = SAMSpecBase()
        status = SAMStatusBase()

        apiVersion = self.loader.get_key(SAMKeys.APIVERSION.value)
        kind = self.loader.get_key(SAMKeys.KIND.value)

        self._manifest = SAM(apiVersion=apiVersion, kind=kind, metadata=metadata, spec=spec, status=status)

    @property
    def manifest(self) -> SAM:
        return self._manifest

    @property
    def loader(self) -> SAMLoader:
        return self._loader
