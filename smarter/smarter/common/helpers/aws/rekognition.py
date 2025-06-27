"""AWS Rekognition helper class."""

from typing import Optional

from smarter.common.exceptions import SmarterConfigurationError

from .aws import AWSBase


class AWSRekognition(AWSBase):
    """AWS Rekognition helper class."""

    _client = None
    _collection_id = None

    def __init__(self, collection_id=None):
        """Initialize the AWS Rekognition helper class."""
        super().__init__()
        self._collection_id = collection_id

    @property
    def client(self):
        """Return the AWS Rekognition client."""
        if not self.aws_session:
            raise SmarterConfigurationError("AWS session is not initialized.")
        if not self._client:
            self._client = self.aws_session.client("rekognition")
        return self._client

    @property
    def collection_id(self):
        """Return the AWS Rekognition collection ID."""
        return self._collection_id

    def get_rekognition_collection_by_id(self, collection_id) -> Optional[str]:
        """Return the Rekognition collection."""
        response = self.client.list_collections()
        for collection in response["CollectionIds"]:
            if collection == collection_id:
                return collection
        return None

    def rekognition_collection_exists(self) -> bool:
        """Test that the Rekognition collection exists."""
        collection = self.get_rekognition_collection_by_id(self.collection_id)
        return collection is not None
