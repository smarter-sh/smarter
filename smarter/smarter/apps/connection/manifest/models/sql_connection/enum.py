"""Enumeration classes for the manifest models."""

from enum import Enum

from smarter.lib.manifest.enum import SmarterEnumAbstract


class DbEngines(SmarterEnumAbstract):
    """SQL database engine enumeration."""

    POSTGRES = "django.db.backends.postgresql"
    MYSQL = "django.db.backends.mysql"
    ORACLE = "django.db.backends.oracle"
    SQLITE = "django.db.backends.sqlite3"
    MSSQL = "django.db.backends.mssql"
    SYBASE = "django.db.backends.sybase"


class DBMSAuthenticationMethods(Enum):
    """SQL database authentication methods enumeration."""

    NONE = "none"
    TCPIP = "tcpip"
    TCPIP_SSH = "tcpip_ssh"
    LDAP_USER_PWD = "ldap_user_pwd"

    @classmethod
    def choices(cls):
        """
        Return the authentication methods as Django model field choices.

        :returns: A list of ``(value, label)`` tuples, where the label is the member name in title case, e.g. ``("tcpip_ssh", "Tcpip Ssh")``.
        """
        return [(method.value, method.name.replace("_", " ").title()) for method in cls]

    @classmethod
    def all(cls):
        """
        Return the values of all authentication methods.

        :returns: A list of the authentication method values.
        """
        return [method.value for method in cls]
