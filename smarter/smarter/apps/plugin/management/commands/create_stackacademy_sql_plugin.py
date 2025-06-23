"""
Command to create a test SQL database connection.
"""

import argparse
import getpass
import re

from django.core.management import call_command
from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account, Secret, UserProfile
from smarter.apps.account.utils import get_cached_smarter_admin_user_profile
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.plugin.manifest.models.sql_connection.enum import (
    DbEngines,
    DBMSAuthenticationMethods,
)
from smarter.apps.plugin.models import SqlConnection
from smarter.common.exceptions import SmarterValueError


KIND = SAMKinds.SQL_CONNECTION.value


def valid_db(value):
    # MySQL database names: 1-64 chars, letters, numbers, _, $
    if not re.match(r"^[A-Za-z0-9_\$]{1,64}$", value):
        raise argparse.ArgumentTypeError(f"Invalid database name: '{value}'")
    return value


def valid_host(value):
    # Accepts IPv4, IPv6, or hostname
    ipv4 = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
    ipv6 = r"^\[?([a-fA-F0-9:]+)\]?$"
    hostname = r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
    if re.match(ipv4, value) or re.match(ipv6, value) or re.match(hostname, value):
        return value
    raise argparse.ArgumentTypeError(f"Invalid host: '{value}'")


def valid_port(value):
    try:
        port = int(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Port must be an integer: '{value}'") from e
    if 1 <= port <= 65535:
        return port
    raise argparse.ArgumentTypeError(f"Port must be between 1 and 65535: '{value}'")


class Command(BaseCommand):
    """
    Django manage.py create_stackacademy_sql_plugin command.
    This command is used to create a SQL database connection.
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--db_host", type=valid_host, required=True, help="The host of the SQL database.")
        parser.add_argument("--db_port", type=valid_port, default=3306, help="The port of the SQL database.")
        parser.add_argument("--db_username", type=str, required=True, help="The username for the SQL database.")
        parser.add_argument("--db_name", type=valid_db, required=True, help="The name of the SQL database connection.")
        parser.add_argument(
            "--db_password", type=str, help="The password for the SQL database. If not provided, you will be prompted."
        )

    def handle(self, *args, **options):
        """Create a test SQL database connection."""

        db_name = options["db_name"]
        host = options["db_host"]
        port = options["db_port"]
        username = options["db_username"]
        password = options.get("db_password")
        if not password:
            password = getpass.getpass("SQL database password: ")
        password = Secret.encrypt(password)

        admin_user_profile: UserProfile = get_cached_smarter_admin_user_profile()
        secret_name = db_name

        # 1.) handle the Secret
        try:
            secret = Secret.objects.get(
                user_profile=admin_user_profile,
                name=secret_name,
            )
            secret.encrypted_value = password
            secret.description = f"Sql database connection pwd for {db_name} at {host}:{port}"
            secret.save()
            self.stdout.write(self.style.SUCCESS(f"Secret '{secret_name}' updated."))

        except Secret.DoesNotExist:
            secret = Secret.objects.create(
                user_profile=admin_user_profile,
                name=secret_name,
                description=f"Sql database connection pwd for {db_name} at {host}:{port}",
                encrypted_value=password,
            )
            self.stdout.write(self.style.SUCCESS(f"Secret '{secret_name}' created successfully."))

        # 2.) handle the SqlConnection
        try:
            sql_connection = SqlConnection.objects.get(
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
            self.stdout.write(self.style.SUCCESS(f"SQL database connection '{db_name}' updated."))
            return
        except SqlConnection.DoesNotExist:
            try:
                SqlConnection.objects.create(
                    account=admin_user_profile.account,
                    name=db_name,
                    kind=KIND,
                    description=f"Sql database connection pwd for {db_name} at {host}:{port}",
                    db_engine=DbEngines.MYSQL.value,
                    authentication_method=DBMSAuthenticationMethods.TCPIP.value,
                    timeout=300,
                    hostname=host,
                    port=3306,
                    database=db_name,
                    username=username,
                    password=secret,
                )
                self.stdout.write(self.style.SUCCESS(f"SQL database connection '{db_name}' created successfully."))
            except SmarterValueError as e:
                self.stdout.write(self.style.ERROR(f"Error creating SQL database connection: {e}"))
                return
        # pylint: disable=W0718
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Unexpected error: {e}"))
            return

        # 3.) handle the Plugin
        # smarter/smarter/apps/plugin/data/sample-plugins/stackademy-sql.yaml
        call_command(
            "create_plugin", account_number=admin_user_profile.account.account_number, username="value2", path="value3"
        )
