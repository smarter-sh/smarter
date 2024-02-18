# -*- coding: utf-8 -*-
"""Signals for plugin app."""
import logging

from django.dispatch import Signal


logger = logging.getLogger(__name__)

plugin_created = Signal()
plugin_updated = Signal()
plugin_deleted = Signal()

logger.info("Signals plugin_created, plugin_updated, plugin_deleted are ready for use.")
