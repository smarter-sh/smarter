"""
Command to create a demo chatbot for the Stackademy API database connection.
"""

import os

from django.core.management import call_command
from django.core.management.base import BaseCommand

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import get_cached_smarter_admin_user_profile
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.const import PROJECT_ROOT


KIND = SAMKinds.SQL_CONNECTION.value


class Command(BaseCommand):
    """
    Django manage.py create_stackademy_api_chatbot command.
    This command is used to create a Chatbot to demo the Stackademy API database plugin.
    """

    def handle(self, *args, **options):
        """Create a chatbot from a manifest file."""
        admin_user_profile: UserProfile = get_cached_smarter_admin_user_profile()

        # 3.) setup the manifest filepath
        file_path = os.path.join(
            PROJECT_ROOT,
            "apps",
            "plugin",
            "data",
            "sample-plugins",
            "chatbot-stackademy-api.yaml",
        )

        # python manage.py apply_manifest --filespec 'smarter/apps/plugin/data/sample-plugins/chatbot-stackademy-api.yaml' --username admin
        call_command(
            "apply_manifest",
            account_number=admin_user_profile.account.account_number,
            username=admin_user_profile.user.username,
            file_path=file_path,
        )
