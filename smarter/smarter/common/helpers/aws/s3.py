"""AWS S3 helper class."""

from .aws import AWSBase


class AWSSimpleStorageSystem(AWSBase):
    """AWS S3 helper class."""

    _client = None

    @property
    def client(self):
        """Return the AWS S3 client."""
        if not self._client:
            self._client = self.aws_session.client("s3")
        return self._client

    def get_bucket_by_prefix(self, bucket_prefix) -> str:
        """Return the bucket name given the bucket prefix."""
        if not self.is_aws_environment:
            return ""
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
        if not self.is_aws_environment:
            return False
        bucket = self.get_bucket_by_prefix(bucket_prefix)
        return bucket is not None
