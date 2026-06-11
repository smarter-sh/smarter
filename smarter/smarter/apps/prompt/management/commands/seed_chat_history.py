"""This module is used to generate seed records for the prompt history models."""

import glob
import os
import secrets
from pathlib import Path

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
)
from smarter.apps.llm_client.models import LLMClient, LLMClientPlugin
from smarter.apps.prompt.models import Prompt
from smarter.apps.provider.services.text_completion.providers import (
    smarter_compatible_client,
)
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SMARTER_EXAMPLE_LLM_CLIENT_NAME
from smarter.lib import json
from smarter.lib.django.management.base import SmarterCommand

HERE = Path(__file__).resolve().parent
default_handler = smarter_compatible_client.default_handler


# pylint: disable=E1101
class Command(SmarterCommand):
    """
    Django manage.py seed_chat_history.py command.

    This command is used to seed the prompt history and audit tables.
    This is only used for local development and testing purposes.
    This command secondarily is a run-time verification of the
    Prompt, LLMClient, Plugin and function calling sub systems.
    """

    def handle(self, *args, **options):
        """
        Handle the command.

        This command is typically invoked as part
        of bootstrapping the local development environment. We need to
        be mindful of we are in the bootstrapping sequence. The
        smarter system account, admin user and profile are *SUPPOSED*
        to exist at this point, as well as the built-in example
        llm_client and plugins.
        """
        self.handle_begin()

        data_folder_path = os.path.join(HERE, "data", "*.json")

        account = Account.objects.get(account_number=SMARTER_ACCOUNT_NUMBER)
        if not account:
            self.handle_completed_failure(msg=f"Account not found: {SMARTER_ACCOUNT_NUMBER}")
            raise ValueError(f"Account not found: {SMARTER_ACCOUNT_NUMBER}")

        user = get_cached_admin_user_for_account(account=account)
        if not user:
            self.handle_completed_failure(msg=f"User not found for account: {account}")
            raise ValueError(f"User not found for account: {account}")

        user_profile = UserProfile.get_cached_object(account=account, user=user)
        if not user_profile:
            self.handle_completed_failure(msg=f"User profile not found for account: {account} user: {user}")
            raise ValueError(f"User profile not found for account: {account} user: {user}")

        llm_client = LLMClient.objects.get(user_profile=user_profile, name=SMARTER_EXAMPLE_LLM_CLIENT_NAME)
        if not llm_client:
            self.handle_completed_failure(msg=f"LLMClient not found {SMARTER_EXAMPLE_LLM_CLIENT_NAME}")
            raise ValueError(f"LLMClient not found {SMARTER_EXAMPLE_LLM_CLIENT_NAME}")

        session_key = "seed_chat_history.py_" + secrets.token_urlsafe(16)
        prompt, _ = Prompt.objects.get_or_create(
            session_key=session_key,
            llm_client=llm_client,
            user_profile=user_profile,
            url="https://localhost:9357/seed-prompt-history",
            ip_address="192.1.1.1",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        )

        for file_path in glob.glob(data_folder_path):
            self.stdout.write(self.style.NOTICE(f"Processing file: {file_path}"))
            with open(file_path, encoding="utf-8") as file:
                data = json.loads(file.read())
                plugins = LLMClientPlugin().plugins(llm_client=llm_client)
                if not plugins or len(plugins) == 0:
                    raise ValueError(
                        f"No plugins found for llm_client: {llm_client}. "
                        "Seeding the prompt history is only useful if the LLMClient has "
                        "one or more plugins. Please check the LLMClientPlugin model."
                    )

                default_handler(prompt=prompt, plugins=plugins, user=user_profile.cached_user, data=data)  # type: ignore
                self.stdout.write(self.style.SUCCESS("Prompt history seeded."))
        self.handle_completed_success()
