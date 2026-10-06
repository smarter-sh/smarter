"""
Test the delete_default_api task, and the receiver that queues it when an llmclient is deleted.

DNS and Kubernetes are never called: destroy_domain_A_record() and the infrastructure services are patched.
"""

import importlib
from unittest.mock import MagicMock, patch

from smarter.apps.account.models import Account
from smarter.apps.llmclient import receivers
from smarter.apps.llmclient.tasks.delete_default_api import delete_default_api
from smarter.lib.unittest.base_classes import SmarterTestBase

MODULE = "smarter.apps.llmclient.tasks.delete_default_api"
# the tasks package exports the task with the module's name, so the module is imported by its path.
task_module = importlib.import_module(MODULE)
ACCOUNT_NUMBER = "3141-5926-5359"
API_URL = f"https://example.{ACCOUNT_NUMBER}.alpha.api.example.com/"


class TestDeleteDefaultApi(SmarterTestBase):
    """Test that the task deletes an llmclient's resources, whether or not its account still exists."""

    def setUp(self):
        super().setUp()
        for name, value in (("is_taskable", True),):
            patcher = patch(f"{MODULE}.{name}", return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch(f"{MODULE}.destroy_domain_A_record")
        self.destroy = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch(f"{MODULE}.infrastructure")
        self.kubernetes = patcher.start().kubernetes
        self.kubernetes.delete_ingress_resources.return_value = (True, True, True)
        self.addCleanup(patcher.stop)

    def assert_deleted(self):
        self.destroy.assert_called_once()
        self.assertEqual(self.destroy.call_args.kwargs["hostname"], f"example.{ACCOUNT_NUMBER}.alpha.api.example.com")
        self.kubernetes.delete_ingress_resources.assert_called_once()

    def test_with_account_number(self):
        with patch(f"{MODULE}.post_delete_default_api") as post:
            delete_default_api(name="example", api_url=API_URL, account_number=ACCOUNT_NUMBER)
        self.assert_deleted()
        self.assertEqual(post.send.call_args.kwargs["account_number"], ACCOUNT_NUMBER)

    def test_deleted_account(self):
        """Test that a task queued with the id of an account that was since deleted still deletes the resources."""
        with patch.object(Account, "get_cached_object", side_effect=Account.DoesNotExist):
            delete_default_api(name="example", api_url=API_URL, account_id=4953)
        self.assert_deleted()

    def test_existing_account_id(self):
        account = MagicMock(account_number=ACCOUNT_NUMBER)
        with patch.object(Account, "get_cached_object", return_value=account):
            delete_default_api(name="example", api_url=API_URL, account_id=1)
        self.assert_deleted()

    def test_resources_not_deleted_are_logged(self):
        self.kubernetes.delete_ingress_resources.return_value = (True, False, True)
        with patch(f"{MODULE}.logger") as logger:
            delete_default_api(name="example", api_url=API_URL, account_number=ACCOUNT_NUMBER)
        logger.error.assert_called_once()

    def test_invalid_url(self):
        """Test that a url that isn't the account's default api url deletes nothing, and isn't retried."""
        for api_url, account_number in (
            ("https://example.com/", None),
            (API_URL, "0000-0000-0000"),
        ):
            with self.subTest(api_url=api_url, account_number=account_number):
                delete_default_api(name="example", api_url=api_url, account_number=account_number)
        self.destroy.assert_not_called()
        self.kubernetes.delete_ingress_resources.assert_not_called()

    def test_not_taskable(self):
        with patch(f"{MODULE}.is_taskable", return_value=False):
            delete_default_api(name="example", api_url=API_URL, account_number=ACCOUNT_NUMBER)
        self.destroy.assert_not_called()

    def test_hostname_helpers(self):
        self.assertEqual(
            task_module._account_number_from_hostname(f"a.{ACCOUNT_NUMBER}.api.example.com"), ACCOUNT_NUMBER
        )  # pylint: disable=protected-access
        self.assertIsNone(task_module._account_number_from_hostname("a.b.c"))  # pylint: disable=protected-access
        self.assertFalse(task_module._is_default_api_hostname("a.b.c", None))  # pylint: disable=protected-access


class TestLLMClientDeletedReceiver(SmarterTestBase):
    """Test that deleting an llmclient queues the task with its account number, on commit."""

    def test_queues_with_account_number(self):
        llmclient = MagicMock()
        llmclient.name = "example"
        llmclient.default_url = API_URL
        llmclient.user_profile.account.account_number = ACCOUNT_NUMBER
        with (
            patch.object(receivers, "delete_default_api") as task,
            patch.object(receivers.transaction, "on_commit", side_effect=lambda func: func()) as on_commit,
        ):
            receivers.llmclient_deleted(sender=None, instance=llmclient)
        on_commit.assert_called_once()
        task.delay.assert_called_once_with(name="example", account_number=ACCOUNT_NUMBER, api_url=API_URL)
