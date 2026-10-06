"""Test SAMSecretBroker's permission checks, not-found branches and failure handling."""

import os
from http import HTTPStatus
from unittest.mock import MagicMock, PropertyMock, patch

from smarter.apps.secret.manifest.brokers.secret import (
    SAMSecretBroker,
    SAMSecretBrokerError,
)
from smarter.apps.secret.manifest.transformers.secret import SecretTransformer
from smarter.apps.secret.models import Secret
from smarter.lib.manifest.broker import SAMBrokerErrorNotFound, SAMBrokerErrorNotReady
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass


class TestSmarterSecretBrokerBranches(TestSAMBrokerBaseClass):
    """Test the SAMSecretBroker branches that the happy-path broker tests don't reach."""

    def setUp(self):
        super().setUp()
        self._broker_class = SAMSecretBroker
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._manifest_filespec = self.get_data_full_filepath("secret.yaml")

    @property
    def SAMBrokerClass(self) -> type[SAMSecretBroker]:
        return SAMSecretBroker

    @property
    def broker(self) -> SAMSecretBroker:
        return super().broker  # type: ignore

    def patch_property(self, name: str, value) -> PropertyMock:
        patcher = patch.object(SAMSecretBroker, name, new_callable=PropertyMock, return_value=value)
        mock = patcher.start()
        self.addCleanup(patcher.stop)
        return mock

    def fake_transformer(self, ready: bool = True, create_error=None, save_error=None) -> MagicMock:
        transformer = MagicMock(spec=SecretTransformer)
        transformer.ready = ready
        transformer.create.side_effect = create_error
        transformer.save.side_effect = save_error
        return transformer

    def admin_broker(self, transformer=None, secret=None) -> SAMSecretBroker:
        broker = self.broker
        self.patch_property("user", self.admin_user)
        self.patch_property("secret_transformer", transformer)
        self.patch_property("secret", secret)
        for name in ("verify_no_dependencies", "cache_invalidations", "to_json"):
            patcher = patch.object(broker, name, return_value={})
            patcher.start()
            self.addCleanup(patcher.stop)
        return broker

    def test_apply_and_delete_require_an_admin(self):
        """Apply and delete refuse a missing or non-staff user."""
        broker = self.broker
        for user in (None, self.non_admin_user):
            with patch.object(SAMSecretBroker, "user", new_callable=PropertyMock, return_value=user):
                for command in ("apply", "delete"):
                    with self.subTest(user=user, command=command), self.assertRaises(SAMSecretBrokerError):
                        getattr(broker, command)(self.request)

    def test_apply_requires_a_manifest(self):
        """Apply isn't ready without a manifest."""
        broker = self.admin_broker(transformer=self.fake_transformer())
        self.patch_property("manifest", None)
        with self.assertRaises(SAMBrokerErrorNotReady):
            broker.apply(self.request)

    def test_apply_requires_a_secret_transformer(self):
        """Apply raises without a SecretTransformer."""
        broker = self.admin_broker(transformer=None)
        with self.assertRaises(SAMSecretBrokerError):
            broker.apply(self.request)

    def test_apply_reports_a_create_failure(self):
        """A failing create() is returned as an error response."""
        broker = self.admin_broker(transformer=self.fake_transformer(create_error=RuntimeError("create failed")))
        self.assertGreaterEqual(broker.apply(self.request).status_code, HTTPStatus.BAD_REQUEST)

    def test_apply_reports_a_save_failure(self):
        """A failing save() is returned as an error response."""
        broker = self.admin_broker(transformer=self.fake_transformer(save_error=RuntimeError("save failed")))
        self.assertGreaterEqual(broker.apply(self.request).status_code, HTTPStatus.BAD_REQUEST)

    def test_apply_reports_a_missing_secret_after_save(self):
        """A save() that leaves no Secret is returned as an error response."""
        broker = self.admin_broker(transformer=self.fake_transformer())
        self.assertGreaterEqual(broker.apply(self.request).status_code, HTTPStatus.BAD_REQUEST)

    def test_apply_saves_and_refreshes_the_secret(self):
        """A ready transformer is saved and the Secret refreshed."""
        secret = MagicMock(spec=Secret)
        broker = self.admin_broker(transformer=self.fake_transformer(), secret=secret)
        self.assertEqual(broker.apply(self.request).status_code, HTTPStatus.OK)
        secret.refresh_from_db.assert_called_once()

    def test_apply_reports_a_transformer_that_isnt_ready(self):
        """A transformer that isn't ready after create() is returned as an error response."""
        broker = self.admin_broker(transformer=self.fake_transformer(ready=False))
        self.assertGreaterEqual(broker.apply(self.request).status_code, HTTPStatus.BAD_REQUEST)

    def test_delete_without_a_secret(self):
        """Delete isn't ready without a Secret."""
        broker = self.admin_broker()
        with self.assertRaises(SAMBrokerErrorNotReady):
            broker.delete(self.request)
        self.assertEqual(broker.dependencies(), [])
        self.assertIsNone(broker.django_orm_to_manifest_dict())

    def test_delete_failure(self):
        """A failing delete() is reported as SAMSecretBrokerError."""
        secret = MagicMock(spec=Secret)
        secret.delete.side_effect = RuntimeError("delete failed")
        broker = self.admin_broker(secret=secret)
        with self.assertRaises(SAMSecretBrokerError):
            broker.delete(self.request)

    def test_describe_without_a_user_profile(self):
        """Describe can't find anything without a user profile."""
        broker = self.broker
        self.patch_property("user_profile", None)
        with self.assertRaises(SAMBrokerErrorNotFound):
            broker.describe(self.request)

    def test_describe_a_secret_that_does_not_exist(self):
        """Describe raises SAMBrokerErrorNotFound for an unknown name."""
        broker = self.broker
        with self.assertRaises(SAMBrokerErrorNotFound):
            broker.describe(self.request, name=f"no_such_secret_{self.hash_suffix}")

    def test_django_orm_to_manifest_dict_needs_an_account_and_user_profile(self):
        """The ORM-to-manifest conversion needs an account and a user profile."""
        broker = self.broker
        self.patch_property("secret", MagicMock(spec=Secret))
        with patch.object(SAMSecretBroker, "account", new_callable=PropertyMock, return_value=None):
            with self.assertRaises(SAMSecretBrokerError):
                broker.django_orm_to_manifest_dict()
        with patch.object(SAMSecretBroker, "user_profile", new_callable=PropertyMock, return_value=None):
            with self.assertRaises(SAMSecretBrokerError):
                broker.django_orm_to_manifest_dict()

    def test_manifest_checks(self):
        """A manifest of the wrong type is rejected, and the conversion to the ORM needs a SAMSecret."""
        broker = self.broker
        broker._manifest = {"kind": "Secret"}  # type: ignore[assignment]
        with self.assertRaises(SAMSecretBrokerError):
            _ = broker.manifest
        broker._manifest = None
        self.patch_property("manifest", None)
        with self.assertRaises(SAMSecretBrokerError):
            broker.manifest_to_django_orm()

    def test_secret_without_a_transformer(self):
        """There's no Secret without a SecretTransformer."""
        broker = self.broker
        self.patch_property("secret_transformer", None)
        self.assertIsNone(broker.secret)
        broker.init_secret()
        self.assertIsNone(broker._manifest)
