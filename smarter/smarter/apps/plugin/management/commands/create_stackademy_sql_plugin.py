"""
Command to create a test SQL database connection.
"""

import getpass
import os

from django.core.management import call_command
from django.core.management.base import BaseCommand

from smarter.apps.account.models import Secret, UserProfile
from smarter.apps.account.utils import get_cached_smarter_admin_user_profile
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.plugin.manifest.models.sql_connection.enum import (
    DbEngines,
    DBMSAuthenticationMethods,
)
from smarter.apps.plugin.models import SqlConnection
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import PROJECT_ROOT
from smarter.lib.django.validators import SmarterValidator


KIND = SAMKinds.SQL_CONNECTION.value


class Command(BaseCommand):
    """
    Django manage.py create_stackacademy_sql_plugin command.
    This command is used to create a SQL database connection.
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "--db_host", type=SmarterValidator.validate_hostname, required=True, help="The host of the SQL database."
        )
        parser.add_argument(
            "--db_name",
            type=SmarterValidator.validate_clean_string,
            required=True,
            help="The name of the SQL database connection.",
        )
        parser.add_argument("--db_username", type=str, required=True, help="The username for the SQL database.")
        parser.add_argument(
            "--db_password", type=str, help="The password for the SQL database. If not provided, you will be prompted."
        )
        parser.add_argument(
            "--db_port", type=SmarterValidator.validate_port, default=3306, help="The port of the SQL database."
        )

    def handle(self, *args, **options):
        """Create a test SQL database connection."""
        self.stdout.write(
            self.style.NOTICE("smarter.apps.plugin.management.commands.create_stackacademy_sql_plugin started.")
        )

        host = options["db_host"]
        if host is None:
            self.stdout.write(self.style.ERROR("The --db_host argument is required."))
            return
        db_name = options["db_name"]
        if db_name is None:
            self.stdout.write(self.style.ERROR("The --db_name argument is required."))
            return
        username = options["db_username"]
        if username is None:
            self.stdout.write(self.style.ERROR("The --db_username argument is required."))
            return
        password = options.get("db_password")
        if not password:
            password = smarter_settings.smarter_mysql_test_database_password
            if not password:
                password = getpass.getpass("SQL database password: ")
        password = Secret.encrypt(password)
        port = options["db_port"]
        if port is None:
            port = 3306

        admin_user_profile: UserProfile = get_cached_smarter_admin_user_profile()
        secret_name = db_name

        # 1.) handle the Secret
        try:
            self.stdout.write(self.style.NOTICE(f"creating Secret '{secret_name}'."))
            secret = Secret.objects.get(
                user_profile=admin_user_profile,
                name=secret_name,
            )
            secret.encrypted_value = password
            secret.description = f"Sql database connection pwd for {db_name} at {host}:{port}"
            secret.save()
            self.stdout.write(self.style.SUCCESS(f"Secret '{secret_name}' updated."))

        except Secret.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(
                    f"Secret '{secret_name}' for account '{admin_user_profile}' does not exist. Creating a new one."
                )
            )
            try:
                secret = Secret.objects.create(
                    user_profile=admin_user_profile,
                    name=secret_name,
                    description=f"Sql database connection pwd for {db_name} at {host}:{port}",
                    encrypted_value=password,
                )
                self.stdout.write(self.style.SUCCESS(f"Secret '{secret_name}' created successfully."))
            # pylint: disable=broad-except
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to create Secret '{secret_name}': {e}"))
                self.stdout.write(
                    self.style.ERROR(
                        "smarter.apps.plugin.management.commands.create_stackacademy_sql_plugin completed with errors."
                    )
                )
                return

        # 2.) handle the SqlConnection
        try:
            self.stdout.write(self.style.NOTICE(f"creating SQL database connection '{db_name}'."))
            sql_connection, created = SqlConnection.objects.get_or_create(
                account=admin_user_profile.account,
                name=db_name,
            )
            sql_connection.kind = KIND
            sql_connection.db_engine = DbEngines.MYSQL.value
            sql_connection.authentication_method = DBMSAuthenticationMethods.TCPIP.value
            sql_connection.timeout = 300
            sql_connection.hostname = host
            sql_connection.port = port
            sql_connection.database = db_name
            sql_connection.username = username
            sql_connection.password = secret
            sql_connection.save()
            if created:
                self.stdout.write(self.style.SUCCESS(f"SQL database connection '{db_name}' created successfully."))
            else:
                self.stdout.write(self.style.SUCCESS(f"SQL database connection '{db_name}' updated."))
        # pylint: disable=W0718
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Unexpected error: {e}"))
            self.stdout.write(
                self.style.ERROR(
                    "smarter.apps.plugin.management.commands.create_stackacademy_sql_plugin completed with errors."
                )
            )
            return

        # 3.) handle the Plugin
        file_path = os.path.join(
            PROJECT_ROOT,
            "apps",
            "plugin",
            "data",
            "stackademy",
            "stackademy-sql.yaml",
        )
        try:
            call_command(
                "create_plugin",
                account_number=admin_user_profile.account.account_number,
                username=admin_user_profile.user.username,
                file_path=file_path,
            )
        # pylint: disable=broad-except
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to create plugin from manifest: {e}"))
            self.stdout.write(
                self.style.ERROR(
                    "smarter.apps.plugin.management.commands.create_stackacademy_sql_plugin completed with errors."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS("smarter.apps.plugin.management.commands.create_stackacademy_sql_plugin completed.")
        )
