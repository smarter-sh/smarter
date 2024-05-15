"""Enumeration classes for the manifest models."""

from smarter.lib.manifest.enum import SmarterEnumAbstract


class DbEngines(SmarterEnumAbstract):
    """SQL database engine enumeration."""

    POSTGRES = "django.db.backends.postgresql"
    MYSQL = "django.db.backends.mysql"
    ORACLE = "django.db.backends.oracle"
    SQLITE = "django.db.backends.sqlite3"
    MSSQL = "django.db.backends.mssql"
    SYBASE = "django.db.backends.sybase"
