"""Smarter API Manifest Broker base class."""

from .loader import SAMLoader
from .models import SAM


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

        # initialize the manifest model
        self._manifest = SAM(**self.loader.data)

    @property
    def manifest(self) -> SAM:
        return self._manifest

    @property
    def loader(self) -> SAMLoader:
        return self._loader
