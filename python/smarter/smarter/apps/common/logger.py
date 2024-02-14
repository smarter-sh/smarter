# -*- coding: utf-8 -*-
"""Platform wide logger configuration."""
# logger.py
import logging
import sys

from django.conf import settings


logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler()])


def get_logger(name):
    """Create a logger object."""
    logger = logging.getLogger(name)

    # Configure the logger to write messages to stdout.
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Set the log level.
    logger.setLevel(settings.LOGGING["root"]["level"])

    return logger
