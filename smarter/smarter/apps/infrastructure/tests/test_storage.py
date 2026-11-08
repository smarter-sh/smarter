"""
Test :mod:`smarter.apps.infrastructure.services.storage`, with the in-memory provider's storage, and.

:class:`~smarter.apps.infrastructure.providers.aws.storage.S3StorageService` with a stubbed S3 client.

The S3 client is a real boto3 client, with fake credentials, whose requests botocore's Stubber answers,
so nothing reaches AWS. A presigned url is computed locally, without a request.
"""

from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import boto3
from botocore.config import Config
from botocore.stub import Stubber

from smarter.apps.infrastructure.const import InfrastructureServiceNames
from smarter.apps.infrastructure.exceptions import (
    InfrastructureNotReadyError,
    StorageServiceError,
)
from smarter.apps.infrastructure.providers.aws import AWSProvider
from smarter.apps.infrastructure.providers.aws.storage import S3StorageService
from smarter.apps.infrastructure.services import infrastructure
from smarter.apps.infrastructure.services.storage import MAX_PRESIGNED_URL_SECONDS
from smarter.apps.infrastructure.signals import infrastructure_operation_failed
from smarter.common.conf import smarter_settings

from .base import InfrastructureTestBase

KEY = "data-exports/1/2/export.zip"
BUCKET = "exports.test.example.com"


def s3_client():
    """Return a real S3 client with fake credentials, for botocore's Stubber."""
    return boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
        config=Config(signature_version="s3v4"),
    )


class TestInMemoryStorageService(InfrastructureTestBase):
    """Test the operations of the storage service, with the in-memory provider's."""

    def setUp(self):
        super().setUp()
        self.storage = self.provider.storage

    def test_facade(self):
        """``infrastructure.storage`` is the provider's storage."""
        self.assertIs(infrastructure.storage, self.storage)
        self.assertEqual(self.storage.service_name, InfrastructureServiceNames.STORAGE)
        self.assertEqual(str(self.storage), "memory.storage")

    def test_put_presign_and_delete(self):
        """An object is saved, shared with a presigned url, and deleted."""
        self.storage.put_object(KEY, b"zip", content_type="application/zip")
        stored = self.storage.objects[KEY]
        self.assertEqual(stored.content, b"zip")
        self.assertEqual(stored.content_type, "application/zip")

        url = self.storage.presigned_url(KEY, expires_in=3600, filename="export.zip")
        query = parse_qs(urlparse(url).query)
        self.assertEqual(query["expires_in"], ["3600"])
        self.assertEqual(query["filename"], ["export.zip"])
        self.assertIn(self.storage.bucket, url)

        url_without_filename = self.storage.presigned_url(KEY, expires_in=60)
        self.assertNotIn("filename", url_without_filename)

        self.storage.delete_object(KEY)
        self.assertNotIn(KEY, self.storage.objects)
        # deleting an object that does not exist is not an error.
        self.storage.delete_object(KEY)

    def test_expiry_out_of_range(self):
        """A presigned url lasts between one second and seven days."""
        for expires_in in (0, MAX_PRESIGNED_URL_SECONDS + 1):
            with self.assertRaises(StorageServiceError):
                self.storage.presigned_url(KEY, expires_in=expires_in)

    def test_not_ready(self):
        """Nothing is saved while the provider is not ready."""
        self.provider.ready = False
        with self.assertRaises(InfrastructureNotReadyError):
            self.storage.put_object(KEY, b"zip")
        self.assertEqual(self.storage.objects, {})

    def test_failures_are_translated(self):
        """A backend's error is raised as StorageServiceError, and announced with a signal."""
        events = self.capture(infrastructure_operation_failed)
        self.storage.fail = "the bucket is gone"
        for call in (
            lambda: self.storage.put_object(KEY, b"zip"),
            lambda: self.storage.presigned_url(KEY, expires_in=60),
            lambda: self.storage.delete_object(KEY),
        ):
            with self.assertRaises(StorageServiceError):
                call()
        operations = [event["operation"] for event in self.sent(events, infrastructure_operation_failed)]
        self.assertEqual(operations, ["put_object", "presigned_url", "delete_object"])


class TestS3StorageService(InfrastructureTestBase):
    """Test the S3 implementation of the storage service, with a stubbed client."""

    def setUp(self):
        super().setUp()
        self.client = s3_client()
        self.stubber = Stubber(self.client)
        self.stubber.activate()
        self.addCleanup(self.stubber.deactivate)
        self.storage = S3StorageService(AWSProvider(), bucket=BUCKET, client=self.client)

    def test_put_object(self):
        """An object is saved encrypted, with its content type."""
        self.stubber.add_response(
            "put_object",
            {},
            {
                "Bucket": BUCKET,
                "Key": KEY,
                "Body": b"zip",
                "ContentType": "application/zip",
                "ServerSideEncryption": "AES256",
            },
        )
        self.storage.put_object(KEY, b"zip", content_type="application/zip")
        self.stubber.assert_no_pending_responses()

    def test_delete_object(self):
        """An object is deleted."""
        self.stubber.add_response("delete_object", {}, {"Bucket": BUCKET, "Key": KEY})
        self.storage.delete_object(KEY)
        self.stubber.assert_no_pending_responses()

    def test_presigned_url(self):
        """A presigned url is signed with Signature Version 4, expires, and names the download."""
        url = self.storage.presigned_url(KEY, expires_in=86400, filename="export.zip")
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        self.assertIn(BUCKET, parsed.netloc + parsed.path)
        self.assertEqual(query["X-Amz-Algorithm"], ["AWS4-HMAC-SHA256"])
        self.assertEqual(query["X-Amz-Expires"], ["86400"])
        self.assertEqual(query["response-content-disposition"], ['attachment; filename="export.zip"'])

        plain = parse_qs(urlparse(self.storage.presigned_url(KEY, expires_in=60)).query)
        self.assertNotIn("response-content-disposition", plain)

    def test_client_error_is_translated(self):
        """An S3 error, e.g. a missing bucket, is raised as StorageServiceError."""
        self.stubber.add_client_error("put_object", service_error_code="NoSuchBucket", http_status_code=404)
        with self.assertRaises(StorageServiceError):
            self.storage.put_object(KEY, b"zip")

    def test_default_bucket(self):
        """The bucket is the environment's private exports bucket, unless one is given."""
        storage = S3StorageService(AWSProvider(), client=self.client)
        self.assertEqual(storage.bucket, smarter_settings.aws_s3_exports_bucket_name)
        self.assertTrue(storage.bucket.startswith("exports."))
        self.assertTrue(storage.ready)

    def test_client_from_provider_session(self):
        """Without a client, one is created from the provider's session, with Signature Version 4."""
        provider = AWSProvider(allow_in_tests=True)
        session = MagicMock()
        with patch.object(AWSProvider, "session", new=session), patch.object(AWSProvider, "ready", new=True):
            storage = provider.storage
            self.assertIsInstance(storage, S3StorageService)
            self.assertIs(provider.storage, storage)
            self.assertTrue(storage.ready)
            client = storage.client
        self.assertIs(client, session.client.return_value)
        args, kwargs = session.client.call_args
        self.assertEqual(args, ("s3",))
        self.assertEqual(kwargs["config"].signature_version, "s3v4")

    def test_client_without_session(self):
        """Without AWS credentials there is no client."""
        provider = AWSProvider(allow_in_tests=True)
        with patch.object(AWSProvider, "session", new=None):
            with self.assertRaises(StorageServiceError):
                _ = S3StorageService(provider).client

    def test_refused_in_unit_tests(self):
        """An AWS provider that isn't allowed in the tests never makes a client, and isn't ready."""
        storage = S3StorageService(AWSProvider())
        self.assertFalse(storage.ready)
        with self.assertRaises(Exception):
            _ = storage.client
