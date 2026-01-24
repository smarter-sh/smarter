"""AWS S3 helper class."""

import logging
from typing import Optional

import botocore.exceptions

from .aws import AWSBase

logger = logging.getLogger(__name__)


class AWSSimpleStorageSystem(AWSBase):
    """
    AWS S3 helper class.
    Provides a high-level interface for managing Amazon Simple Storage Service (S3) resources.

    This helper class abstracts common operations related to AWS S3, such as retrieving and verifying S3 buckets,
    and managing connections to the S3 service. It simplifies interactions with the AWS S3 API by encapsulating
    client initialization and error handling, making it easier to integrate S3 management into automation workflows
    or larger AWS orchestration systems.

    The class is designed to work with application configuration settings and ensures that AWS sessions are properly
    initialized before performing any operations. It supports robust and maintainable code by providing logging and
    exception handling for operations involving S3 resources, such as bucket discovery and validation, within AWS
    environments.
    """

    _client = None
    _client_type: str = "s3"

    def get_bucket_by_prefix(self, bucket_prefix) -> Optional[str]:
        """
        Return the bucket name given the bucket prefix.

        :param bucket_prefix: S3 bucket prefix
        :return: S3 bucket ARN or None if not found
        """
        try:
            for bucket in self.client.list_buckets()["Buckets"]:
                if bucket["Name"].startswith(bucket_prefix):
                    return f"arn:aws:s3:::{bucket['Name']}"
        except TypeError:
            # TypeError: startswith first arg must be str or a tuple of str, not NoneType
            pass
        return None

    def bucket_exists(self, bucket_prefix) -> bool:
        """
        Test that the S3 bucket exists.

        :param bucket_prefix: S3 bucket prefix
        :return: True if the bucket exists, else False
        """
        bucket = self.get_bucket_by_prefix(bucket_prefix)
        return bucket is not None
