# -*- coding: utf-8 -*-
"""Signals for account app."""
import logging

from django.dispatch import Signal


logger = logging.getLogger(__name__)

new_user_created = Signal()
logger.info("Signal new_user_created is ready for use.")
