"""Test SAMUserBroker's permission checks, not-found branches, deploy/undeploy and dependencies."""

import os
from unittest.mock import MagicMock, PropertyMock, patch

from smarter.apps.account.manifest.brokers.user import SAMUserBroker, SAMUserBrokerError
from smarter.apps.account.models import User
from smarter.lib.manifest.broker import SAMBrokerErrorNotFound, SAMBrokerErrorNotReady
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass

ADMIN_COMMANDS = ("apply", "delete", "deploy", "undeploy")


class TestSmarterUserBrokerPermissions(TestSAMBrokerBaseClass):
    """Test the SAMUserBroker branches that the happy-path broker tests don't reach."""

    def setUp(self):
        super().setUp()
        self._broker_class = SAMUserBroker
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._manifest_filespec = self.get_data_full_filepath("user.yaml")

    @property
    def SAMBrokerClass(self) -> type[SAMUserBroker]:
        return SAMUserBroker

    @property
    def broker(self) -> SAMUserBroker:
        return super().broker  # type: ignore

    def patch_property(self, name: str, value) -> PropertyMock:
        patcher = patch.object(SAMUserBroker, name, new_callable=PropertyMock, return_value=value)
        mock = patcher.start()
        self.addCleanup(patcher.stop)
        return mock

    def throwaway_user(self, is_active: bool) -> User:
        user = User.objects.create(username=f"test_user_broker_perm_{self._testMethodName}"[:150], is_active=is_active)
        self.addCleanup(user.delete)
        return user

    def test_admin_commands_require_a_user(self):
        """Apply, delete, deploy and undeploy refuse a request without a User."""
        broker = self.broker
        self.patch_property("user", None)
        for command in ADMIN_COMMANDS:
            with self.subTest(command=command), self.assertRaises(SAMUserBrokerError):
                getattr(broker, command)(self.request)

    def test_admin_commands_require_staff(self):
        """Apply, delete, deploy and undeploy refuse a non-staff user."""
        broker = self.broker
        self.patch_property("user", self.non_admin_user)
        for command in ADMIN_COMMANDS:
            with self.subTest(command=command), self.assertRaises(SAMUserBrokerError):
                getattr(broker, command)(self.request)

    def test_commands_without_a_brokered_user(self):
        """Deploy and undeploy aren't ready, and delete and describe find nothing, without a brokered user."""
        broker = self.broker
        self.patch_property("user", self.admin_user)
        self.patch_property("brokered_user", None)
        for command in ("deploy", "undeploy"):
            with self.subTest(command=command), self.assertRaises(SAMBrokerErrorNotReady):
                getattr(broker, command)(self.request)
        for command in ("delete", "describe"):
            with self.subTest(command=command), self.assertRaises(SAMBrokerErrorNotFound):
                getattr(broker, command)(self.request)
        self.assertEqual(broker.dependencies(), [])

    def test_deploy_and_undeploy(self):
        """Deploy activates the brokered user and undeploy deactivates it."""
        user = self.throwaway_user(is_active=False)
        broker = self.broker
        self.patch_property("user", self.admin_user)
        self.patch_property("brokered_user", user)
        self.assertEqual(broker.deploy(self.request).status_code, 200)
        self.assertTrue(User.objects.get(pk=user.pk).is_active)
        self.assertEqual(broker.undeploy(self.request).status_code, 200)
        self.assertFalse(User.objects.get(pk=user.pk).is_active)

    def test_deploy_failure(self):
        """A failed save is reported as a SAMUserBrokerError."""
        broker = self.broker
        self.patch_property("user", self.admin_user)
        failing_user = MagicMock(is_active=False, email="x@example.com")
        failing_user.save.side_effect = RuntimeError("boom")
        self.patch_property("brokered_user", failing_user)
        with self.assertRaises(SAMUserBrokerError):
            broker.deploy(self.request)
        failing_user.is_active = True
        with self.assertRaises(SAMUserBrokerError):
            broker.undeploy(self.request)

    def test_dependencies_of_a_user(self):
        """A user with no resources has no dependencies."""
        user = self.throwaway_user(is_active=True)
        broker = self.broker
        self.patch_property("brokered_user", user)
        self.assertEqual(broker.dependencies(), [])

    def test_manifest_required(self):
        """Apply, describe and the ORM conversions need a manifest."""
        broker = self.broker
        self.patch_property("user", self.admin_user)
        self.patch_property("manifest", None)
        with self.assertRaises(SAMUserBrokerError):
            broker.apply(self.request)
        with self.assertRaises(SAMUserBrokerError):
            broker.describe(self.request)
        with self.assertRaises(SAMUserBrokerError):
            broker.manifest_to_django_orm()
        with self.assertRaises(SAMUserBrokerError):
            broker.django_orm_to_manifest_dict()

    def test_manifest_of_the_wrong_type(self):
        """A manifest that isn't a SAMUser is rejected."""
        broker = self.broker
        broker._manifest = {"kind": "User"}  # type: ignore[assignment]
        with self.assertRaises(SAMUserBrokerError):
            _ = broker.manifest
