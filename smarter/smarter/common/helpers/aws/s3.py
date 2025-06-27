"""AWS S3 helper class."""

from typing import Optional

from .aws import AWSBase, SmarterAWSException


class AWSSimpleStorageSystem(AWSBase):
    """AWS S3 helper class."""

    _client = None

    @property
    def client(self):
        """Return the AWS S3 client."""
        if not self.aws_session:
            raise SmarterAWSException("AWS session is not initialized.")
        if not self._client:
            self._client = self.aws_session.client("s3")
        return self._client

    def get_bucket_by_prefix(self, bucket_prefix) -> Optional[str]:
        """Return the bucket name given the bucket prefix."""
        try:
            for bucket in self.client.list_buckets()["Buckets"]:
                if bucket["Name"].startswith(bucket_prefix):
                    return f"arn:aws:s3:::{bucket['Name']}"
        except TypeError:
            # TypeError: startswith first arg must be str or a tuple of str, not NoneType
            pass
        return None

    def bucket_exists(self, bucket_prefix) -> bool:
        """Test that the S3 bucket exists."""
        bucket = self.get_bucket_by_prefix(bucket_prefix)
        return bucket is not None
