"""
Command to create a demo chatbot for the Stackademy API database connection.
"""

import io
import os

from django.core.management import call_command

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import get_cached_smarter_admin_user_profile
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.const import PROJECT_ROOT
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.management.base import SmarterCommand


KIND = SAMKinds.API_CONNECTION.value


class Command(SmarterCommand):
    """
    Django manage.py create_stackademy_api_chatbot command.
    This command is used to create a Chatbot to demo the Stackademy API database plugin.
    """

    def handle(self, *args, **options):
        """Create a chatbot from a manifest file."""
        self.handle_begin()

        admin_user_profile: UserProfile = get_cached_smarter_admin_user_profile()
        output = io.StringIO()
        error_output = io.StringIO()

        # 3.) setup the manifest filepath
        file_path = os.path.join(
            PROJECT_ROOT,
            "apps",
            "plugin",
            "data",
            "stackademy",
            "chatbot-stackademy-api.yaml",
        )

        try:
            # python manage.py apply_manifest --filespec 'smarter/apps/plugin/data/stackademy/chatbot-stackademy-api.yaml' --username admin
            call_command(
                "apply_manifest",
                username=admin_user_profile.user.username,
                filespec=file_path,
                stdout=output,
                stderr=error_output,
            )
            if error_output.getvalue():
                print(f"Command completed with warnings: {error_output.getvalue()}")
            else:
                print(f"Applied manifest {file_path}. output: {output.getvalue()}")
        except Exception as exc:
            self.handle_completed_failure(err=exc)
            raise SmarterValueError(f"Failed to apply manifest: {exc}") from exc

        self.handle_completed_success()
