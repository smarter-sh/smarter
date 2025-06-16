"""
Command to create a test SQL database connection.
"""

import argparse
import getpass
import re

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Secret
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
    Django manage.py create_sqldb_connection command.
    This command is used to create a SQL database connection.
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--host", type=valid_host, required=True, help="The host of the SQL database.")
        parser.add_argument("--port", type=valid_port, default=3306, help="The port of the SQL database.")
        parser.add_argument("--username", type=str, required=True, help="The username for the SQL database.")
        parser.add_argument(
            "--password", type=str, help="The password for the SQL database. If not provided, you will be prompted."
        )
        parser.add_argument("--db", type=valid_db, required=True, help="The name of the SQL database connection.")

    def handle(self, *args, **options):
        """Create a test SQL database connection."""

        db = options["db"]
        host = options["host"]
        port = options["port"]
        username = options["username"]
        password = options.get("password")
        if not password:
            password = getpass.getpass("SQL database password: ")
        password = Secret.encrypt(password)

        user_profile = get_cached_smarter_admin_user_profile()
        name = db

        try:
            secret = Secret.objects.get(
                user_profile=user_profile,
                name=name,
            )
            secret.encrypted_value = password
            secret.description = f"Sql database connection pwd for {db} at {host}:{port}"
            secret.save()
            self.stdout.write(self.style.SUCCESS(f"Secret '{name}' updated."))

        except Secret.DoesNotExist:
            secret = Secret.objects.create(
                user_profile=user_profile,
                name=name,
                description=f"Sql database connection pwd for {db} at {host}:{port}",
                encrypted_value=password,
            )
            self.stdout.write(self.style.SUCCESS(f"Secret '{name}' created successfully."))

        try:
            sql_connectin = SqlConnection.objects.get(
                account=user_profile.account,
                name=name,
            )
            sql_connectin.kind = KIND
            sql_connectin.db_engine = DbEngines.MYSQL.value
            sql_connectin.authentication_method = DBMSAuthenticationMethods.TCPIP.value
            sql_connectin.timeout = 300
            sql_connectin.hostname = host
            sql_connectin.port = port
            sql_connectin.database = db
            sql_connectin.username = username
            sql_connectin.password = secret
            sql_connectin.save()
            self.stdout.write(self.style.SUCCESS(f"SQL database connection '{name}' updated."))
            return
        except SqlConnection.DoesNotExist:
            try:
                SqlConnection.objects.create(
                    account=user_profile.account,
                    name=name,
                    kind=KIND,
                    description=f"Sql database connection pwd for {db} at {host}:{port}",
                    db_engine=DbEngines.MYSQL.value,
                    authentication_method=DBMSAuthenticationMethods.TCPIP.value,
                    timeout=300,
                    hostname=host,
                    port=3306,
                    database=db,
                    username=username,
                    password=secret,
                )
                self.stdout.write(self.style.SUCCESS(f"SQL database connection '{name}' created successfully."))
            except SmarterValueError as e:
                self.stdout.write(self.style.ERROR(f"Error creating SQL database connection: {e}"))
                return
