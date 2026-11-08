"""
The storage service of AWS: the environment's private S3 bucket of exports.

:class:`S3StorageService` implements the primitives of
:class:`~smarter.apps.infrastructure.services.storage.StorageService` with an S3 client of the AWS
provider's boto3 session. Its bucket, ``smarter_settings.aws_s3_exports_bucket_name``, is created by
smarter-infrastructure: it blocks all public access, encrypts its objects, and deletes them after a
day. A presigned url is signed with Signature Version 4, which AWS requires for urls that last
longer than an hour.
"""

from typing import TYPE_CHECKING, Any, Optional

from botocore.config import Config

from smarter.common.conf import smarter_settings

from ...services.storage import StorageService

if TYPE_CHECKING:
    from .provider import AWSProvider


class S3StorageService(StorageService):
    """
    AWS S3, as the platform's private object storage.

    :param provider: The AWS provider, which authenticates with AWS.
    :param bucket: The bucket, by default ``smarter_settings.aws_s3_exports_bucket_name``.
    :param client: An S3 client, e.g. one that a test stubs, or None for one of the provider's session.
    """

    def __init__(
        self,
        provider: "AWSProvider",
        bucket: Optional[str] = None,
        client: Optional[Any] = None,
        **kwargs,
    ):
        super().__init__(provider.provider_name, **kwargs)
        self.provider = provider
        self._bucket = bucket
        self._client = client

    @property
    def ready(self) -> bool:
        """Whether the AWS provider is ready, i.e. authenticated with AWS."""
        if self._client is not None:
            return True
        return self.provider.ready

    @property
    def bucket(self) -> str:
        """The private bucket, ``smarter_settings.aws_s3_exports_bucket_name`` unless one was given."""
        if self._bucket:
            return self._bucket
        return smarter_settings.aws_s3_exports_bucket_name

    @property
    def client(self) -> Any:
        """The S3 client, created from the provider's boto3 session when it is first used."""
        if self._client is None:
            self.provider.require_live()
            session = self.provider.session
            if session is None:
                raise self.error_class("AWS is not configured, so there is no S3 client.")
            config = Config(signature_version="s3v4")
            self._client = session.client("s3", region_name=smarter_settings.aws_region, config=config)
            self.connection_state(True)
        return self._client

    def _put_object(self, key: str, content: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )

    def _presigned_url(self, key: str, expires_in: int, filename: Optional[str]) -> str:
        params = {"Bucket": self.bucket, "Key": key}
        if filename:
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'
        url = self.client.generate_presigned_url("get_object", Params=params, ExpiresIn=expires_in)
        return str(url)

    def _delete_object(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


__all__ = ["S3StorageService"]
