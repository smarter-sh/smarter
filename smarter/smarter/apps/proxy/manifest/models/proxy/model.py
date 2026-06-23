"""Smarter API Proxy Manifest."""

from typing import ClassVar

from pydantic import Field

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .const import MANIFEST_KIND
from .spec import SAMProxySpec

MODULE_IDENTIFIER = MANIFEST_KIND


logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])


class SAMProxy(AbstractSAMBase):
    """Smarter API Proxy Manifest."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    spec: SAMProxySpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
