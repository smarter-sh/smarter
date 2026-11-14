"""Test SAMUserBroker's permission checks, not-found branches, deploy/undeploy and dependencies."""

import os
from unittest.mock import MagicMock, PropertyMock, patch

from smarter.apps.account.manifest.brokers.user import SAMUserBroker, SAMUserBrokerError
from smarter.apps.account.models import User, UserProfile
from smarter.lib.journal.enum import SmarterJournalCliCommands
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
        return super().broker  # type: ignore[return-value]

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

    def test_account_admin_may_apply(self):
        """A user whose profile has is_account_admin may apply a User manifest, though they aren't staff."""
        member = UserProfile.objects.get(pk=self.non_admin_user_profile.pk)
        member.is_account_admin = True
        broker = self.broker
        self.patch_property("user", self.non_admin_user)
        self.patch_property("user_profile", member)
        self.patch_property("account", self.account)
        self.patch_property("brokered_user", None)
        # check_authority_over_user() lets it through; nothing else is under test here.
        broker.check_authority_over_user(SmarterJournalCliCommands.APPLY)
        self.assertTrue(broker.administers_account)

    def test_another_accounts_user_is_refused(self):
        """An account's administrator can't change a user who doesn't belong to their account."""
        outsider = self.throwaway_user(is_active=True)
        broker = self.broker
        self.patch_property("user", self.non_admin_user)
        self.patch_property("account", self.account)
        self.patch_property("brokered_user", outsider)
        with self.assertRaisesRegex(SAMUserBrokerError, "belongs to another account"):
            broker.check_authority_over_user(SmarterJournalCliCommands.APPLY)

    def test_only_staff_change_is_staff(self):
        """An account administrator who isn't staff can't make a user staff, themselves included."""
        broker = self.broker
        self.patch_property("user", self.non_admin_user)
        self.patch_property("account", self.account)
        self.patch_property("brokered_user", self.non_admin_user)
        manifest = broker.manifest
        assert manifest is not None
        config = manifest.spec.config.model_copy(update={"isStaff": True})
        spec = manifest.spec.model_copy(update={"config": config})
        self.patch_property("manifest", manifest.model_copy(update={"spec": spec}))
        with self.assertRaisesRegex(SAMUserBrokerError, "Only staff may change whether a user is staff"):
            broker.check_authority_over_user(SmarterJournalCliCommands.APPLY)

    def test_superuser_may_change_anyone(self):
        """A superuser's User manifest may reach any user."""
        outsider = self.throwaway_user(is_active=True)
        broker = self.broker
        self.patch_property("user", self.admin_user)
        self.patch_property("brokered_user", outsider)
        broker.check_authority_over_user(SmarterJournalCliCommands.APPLY)

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
        with self.assertRaises(SAMBrokerErrorNotFound):
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
