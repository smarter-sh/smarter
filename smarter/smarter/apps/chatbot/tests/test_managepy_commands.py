"""Tests for manage.py create_plugin."""

import hashlib
import random
import time
import unittest

from django.core.management import call_command

from smarter.apps.account.models import Account, SmarterAuthToken
from smarter.apps.account.tests.factories import admin_user_factory, admin_user_teardown
from smarter.apps.chatbot.models import ChatBot, ChatBotAPIKey
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SMARTER_EXAMPLE_CHATBOT_NAME


class ManageCommandCreatePluginTestCase(unittest.TestCase):
    """Tests for manage.py create_plugin."""

    def setUp(self):
        """Set up test fixtures."""
        hashed_slug = hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()[:16]
        self.user, self.account, self.user_profile = admin_user_factory()
        self.auth_token, self.secret_key = SmarterAuthToken.objects.create(
            account=self.account, user=self.user, description="unit test"
        )
        self.chatbot = ChatBot.objects.create(
            account=self.account,
            name=f"{hashed_slug}",
        )

    def tearDown(self):
        """Clean up test fixtures."""
        admin_user_teardown(self.user, self.account, self.user_profile)

    def test_add_api_key(self):

        call_command(
            "add_api_key",
            "--account_number",
            f"{self.account.account_number}",
            "--key_id",
            self.auth_token.key_id,
            "--name",
            self.chatbot.name,
        )

        chatbot_api_key = ChatBotAPIKey.objects.get(api_key=self.auth_token)
        self.assertEqual(chatbot_api_key.chatbot, self.chatbot)

    def test_deploy_api_key(self):

        call_command("deploy_api", "--account_number", f"{self.account.account_number}", "--name", self.chatbot.name)

    def test_deploy_demo_api(self):

        call_command("deploy_demo_api")
        smarter_account = Account.objects.get(account_number=SMARTER_ACCOUNT_NUMBER)
        chatbot = ChatBot.objects.get(name=SMARTER_EXAMPLE_CHATBOT_NAME, account=smarter_account)
        self.assertTrue(chatbot.deployed)

    def test_initialize_waffle(self):

        call_command("initialize_waffle")

    def test_load_from_github(self):

        call_command(
            "load_from_github",
            "--account_number",
            f"{self.account.account_number}",
            "--url",
            "https://github.com/QueriumCorp/smarter-demo",
            "--username",
            self.user.get_username(),
        )

    def test_verify_api_infrastructure(self):

        call_command("verify_api_infrastructure")
