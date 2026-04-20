# pylint: disable=W0613,C0302
"""Smarter API Manifest Abstract Broker class."""

import logging
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from http import HTTPStatus
from typing import Any, Optional, Type, Union
from urllib.parse import parse_qs, urlparse

import inflect
from django.core import serializers
from django.core.handlers.wsgi import WSGIRequest
from django.db import IntegrityError, models
from django.http import HttpRequest, QueryDict
from requests import PreparedRequest
from rest_framework.request import Request
from rest_framework.serializers import ModelSerializer

from smarter.apps.account.models import (
    Account,
    MetaDataWithOwnershipModel,
    User,
    UserProfile,
)
from smarter.apps.account.signals import cache_invalidate
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
    smarter_cached_objects,
)
from smarter.apps.secret.models import Secret
from smarter.common.api import SmarterApiVersions
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text, formatted_text_blue
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.mixins import SmarterConverterMixin
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import (
    SmarterJournalApiResponseErrorKeys,
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
    SmarterJournalThings,
)
from smarter.lib.journal.http import (
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
)
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.models import AbstractSAMBase

from ..exceptions import SAMExceptionBase

inflect_engine = inflect.engine()

SUPPORTED_API_VERSIONS = [SmarterApiVersions.V1]


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.MANIFEST_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class SAMBrokerError(SAMExceptionBase):
    """Base class for all SAMBroker errors."""

    thing: Optional[Union[SmarterJournalThings, str]] = None
    command: Optional[SmarterJournalCliCommands] = None
    stack_trace: Optional[str] = None

    def __init__(
        self,
        message: Optional[str] = None,
        thing: Optional[Union[SmarterJournalThings, str]] = None,
        command: Optional[SmarterJournalCliCommands] = None,
        stack_trace: Optional[str] = None,
    ):
        self.thing = thing
        self.command = command
        self.stack_trace = stack_trace
        super().__init__(message or "")

    @property
    def get_formatted_err_message(self):
        msg = f"Smarter API {self.thing} manifest broker: {self.command}() unidentified error."
        if self.message:
            msg += "  " + self.message
        return msg


class SAMBrokerReadOnlyError(SAMBrokerError):
    """Error for read-only broker operations."""

    @property
    def get_formatted_err_message(self):
        msg = f"Smarter API {self.thing} manifest broker: {self.command}() read-only error."
        if self.message:
            msg += "  " + self.message
        return msg


class SAMBrokerErrorNotImplemented(SAMBrokerError):
    """Base class for all SAMBroker errors."""

    @property
    def get_formatted_err_message(self):
        msg = f"Smarter API {self.thing} manifest broker: {self.command}() not implemented error."
        if self.message:
            msg += "  " + self.message
        return msg


class SAMBrokerErrorNotReady(SAMBrokerError):
    """Error for broker operations on resources that are not ready."""

    @property
    def get_formatted_err_message(self):
        msg = f"Smarter API {self.thing} manifest broker: {self.command}() not ready error."
        if self.message:
            msg += "  " + self.message
        return msg


class SAMBrokerErrorNotFound(SAMBrokerError):
    """Error for broker operations on resources that are not found."""

    @property
    def get_formatted_err_message(self):
        msg = f"Smarter API {self.thing} manifest broker: {self.command}() not found error."
        if self.message:
            msg += "  " + self.message
        return msg


class SAMBrokerInternalError(SAMBrokerError):
    """
    Error for broker operations that result in an internal error,
    such as trying to create a resource that already exists.
    """

    @property
    def get_formatted_err_message(self):
        msg = f"Smarter API {self.thing} manifest broker: {self.command}() internal error."
        if self.message:
            msg += "  " + self.message
        return msg


__all__ = [
    "SAMBrokerError",
    "SAMBrokerReadOnlyError",
    "SAMBrokerErrorNotImplemented",
    "SAMBrokerErrorNotReady",
    "SAMBrokerErrorNotFound",
    "SAMBrokerInternalError",
]
