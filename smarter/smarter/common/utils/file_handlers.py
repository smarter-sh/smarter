"""
Utility functions for the Smarter framework.

This module provides a collection of helper functions and classes
that are ostensibly implemented in more than one Smarter base class.
Hence, they are only here in order to keep the code DRY (Don't Repeat Yourself).

The module is intended for internal use within the Smarter framework and is
designed to be compatible with Python 3, Django, DRF, and Pydantic.

"""

import asyncio
import csv
import logging

import yaml

from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

logger = logging.getLogger(__name__)
logger_prefix = formatted_text(__name__)


# pylint: disable=W0613
def should_log_verbose(level):
    """Check if logging should be done based on the waffle switch."""
    # pylint: disable=C0415
    from smarter.common.conf import smarter_settings

    return smarter_settings.verbose_logging


verbose_logger = WaffleSwitchedLoggerWrapper(logger, should_log_verbose)


def is_async_context():
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


def get_readonly_yaml_file(file_path) -> dict:
    """
    Reads a YAML file from the specified path and returns its contents as a Python dictionary.

    :param file_path: The path to the YAML file to be read. This should be a string representing a valid file system path.
    :type file_path: str

    :return: The contents of the YAML file, parsed into a Python dictionary. If the file is empty or contains no valid YAML, ``None`` may be returned.
    :rtype: dict

    .. note::
        This function opens the file in read-only mode with UTF-8 encoding and uses ``yaml.safe_load`` for parsing. Only standard YAML types are supported.

    .. warning::
        If the file does not exist, is not readable, or contains invalid YAML, an exception will be raised. Always validate the file path and contents before use.

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import get_readonly_yaml_file

        config = get_readonly_yaml_file('/path/to/config.yaml')
        print(config)  # {'key': 'value', ...}

    """
    logger.debug("%s.get_readonly_yaml_file()", logger_prefix)
    with open(file_path, encoding="utf-8") as file:
        return yaml.safe_load(file)


def get_readonly_csv_file(file_path):
    """
    Reads a CSV file from the specified path and returns its contents as a list of dictionaries.

    :param file_path: The path to the CSV file to be read. This should be a string representing a valid file system path.
    :type file_path: str

    :return: A list of dictionaries, where each dictionary represents a row in the CSV file. The keys of each dictionary correspond to the column headers in the CSV.
    :rtype: list[dict]

    .. note::
        The file is opened in read-only mode with UTF-8 encoding. The function uses ``csv.DictReader`` to parse the file, which means the first row must contain the column headers.

    .. warning::
        If the file does not exist, is not readable, or is not a valid CSV, an exception will be raised. Always validate the file path and ensure the CSV is properly formatted.

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import get_readonly_csv_file

        rows = get_readonly_csv_file('/path/to/data.csv')
        for row in rows:
            print(row)  # {'column1': 'value1', 'column2': 'value2', ...}
    """
    with open(file_path, encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)


__all__ = [
    "get_readonly_csv_file",
    "get_readonly_yaml_file",
]
