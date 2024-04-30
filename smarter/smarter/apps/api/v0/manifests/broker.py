"""Smarter API Manifest Handler base class."""

import logging

from .enum import SAMKeys
from .loader import SAMLoader
from .models import SAM, SAMMetadataBase, SAMSpecBase, SAMStatusBase


logger = logging.getLogger(__name__)


###############################################################################
# Handler
###############################################################################
class SAMBroker:
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
        apiVersion = self.loader.get_key(SAMKeys.APIVERSION.value)
        kind = self.loader.get_key(SAMKeys.KIND.value)

        metadata_dict = self.loader.manifest_metadata()
        metadata = SAMMetadataBase(**metadata_dict)

        spec_dict = self.loader.manifest_spec()
        spec = SAMSpecBase(**spec_dict)

        status_dict = self.loader.manifest_status()
        status = SAMStatusBase(**status_dict)

        self._manifest = SAM(
            manifest=self.loader.data, apiVersion=apiVersion, kind=kind, metadata=metadata, spec=spec, status=status
        )

    @property
    def manifest(self) -> SAM:
        return self._manifest

    @property
    def loader(self) -> SAMLoader:
        return self._loader
