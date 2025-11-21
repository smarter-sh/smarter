"""
Command to create a test Api connection.
"""

import getpass

from django.core.management import call_command

from smarter.apps.account.models import Secret, UserProfile
from smarter.apps.account.utils import get_cached_smarter_admin_user_profile
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.plugin.manifest.models.api_connection.enum import AuthMethods
from smarter.apps.plugin.models import ApiConnection
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.django.validators import SmarterValidator


KIND = SAMKinds.API_CONNECTION.value


class Command(SmarterCommand):
    """
    Django manage.py create_stackacademy_api_plugin command.
    This command is used to create a Api connection.
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "--api_host", type=SmarterValidator.validate_hostname, required=True, help="The host of the Api."
        )
        parser.add_argument(
            "--api_port", type=SmarterValidator.validate_port, default=3306, help="The port of the Api."
        )
        parser.add_argument(
            "--api_key", type=str, help="The authentication key for the Api. If not provided, you will be prompted."
        )

    def handle(self, *args, **options):
        """Create a test Api connection."""
        self.handle_begin()

        api_name = options["api_name"]
        host = options["api_host"]
        port = options["api_port"]
        username = options["api_username"]
        api_key = options.get("api_key")
        if not api_key:
            api_key = getpass.getpass("Api api_key: ")
        api_key = Secret.encrypt(api_key)

        admin_user_profile: UserProfile = get_cached_smarter_admin_user_profile()
        secret_name = api_name

        # 1.) handle the Secret
        try:
            secret = Secret.objects.get(
                user_profile=admin_user_profile,
                name=secret_name,
            )
            secret.encrypted_value = api_key
            secret.description = f"Api authentication key for {api_name} at {host}:{port}"
            secret.save()
            self.stdout.write(self.style.SUCCESS(f"Secret '{secret_name}' updated."))

        except Secret.DoesNotExist:
            secret = Secret.objects.create(
                user_profile=admin_user_profile,
                name=secret_name,
                description=f"Api authentication key for {api_name} at {host}:{port}",
                encrypted_value=api_key,
            )
            self.handle_completed_success(msg=f"Secret '{secret_name}' created successfully.")

        # 2.) handle the ApiConnection
        try:
            api_connection, created = ApiConnection.objects.get_or_create(
                account=admin_user_profile.account,
                name=api_name,
            )
            api_connection.kind = KIND
            api_connection.auth_method = AuthMethods.TOKEN.value
            api_connection.timeout = 300
            api_connection.proxy_host = host
            api_connection.proxy_host = port
            api_connection.name = api_name
            api_connection.proxy_username = username
            api_connection.proxy_password = secret
            api_connection.save()
            if created:
                self.handle_completed_success(msg=f"API connection '{api_name}' created successfully.")
            else:
                self.handle_completed_success(msg=f"Api connection '{api_name}' updated successfully.")
        # pylint: disable=W0718
        except Exception as e:
            self.handle_completed_failure(e)
            return

        # 3.) handle the Plugin
        try:
            call_command(
                "create_plugin",
                account_number=admin_user_profile.account.account_number,
                username=admin_user_profile.user.username,
                path="./smarter/smarter/apps/plugin/data/stackademy/stackademy-api.yaml",
            )
        # pylint: disable=W0718
        except Exception as e:
            self.handle_completed_failure(e)
            return

        self.handle_completed_success()
