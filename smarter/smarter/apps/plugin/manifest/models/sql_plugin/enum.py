"""Enumeration classes for the manifest models."""

from smarter.lib.manifest.enum import SmarterEnumAbstract


class SAMSqlPluginSpecSqlData(SmarterEnumAbstract):
    """spec.apiData"""

    SQL_QUERY = "sqlQuery"
    PARAMETERS = "parameters"
    TEST_VALUES = "testValues"
    LIMIT = "limit"
