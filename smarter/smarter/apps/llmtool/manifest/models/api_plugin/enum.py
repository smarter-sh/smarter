"""Enumeration classes for the manifest models."""

from smarter.lib.manifest.enum import SmarterEnumAbstract


class SAMApiPluginSpecApiData(SmarterEnumAbstract):
    """Spec.apiData."""

    ENDPOINT = "endpoint"
    PARAMETERS = "parameters"
    HEADERS = "headers"
    BODY = "body"
    TEST_VALUES = "test_values"
    LIMIT = "limit"
