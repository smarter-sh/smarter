"""Enumeration classes for the manifest models."""

from smarter.lib.manifest.enum import SmarterEnumAbstract


class DbEngine(SmarterEnumAbstract):
    """SQL database engine enumeration."""

    POSTGRES = "postgres"
    MYSQL = "mysql"
    ORACLE = "oracle"
    SQLITE = "sqlite"
    MSSQL = "mssql"
