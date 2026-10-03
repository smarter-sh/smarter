"""Smarter API Manifest - Guardrail.status."""

import datetime
import os
from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.guardrail.manifest.models.guardrail.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMStatusBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMGuardrailStatus(AbstractSAMStatusBase):
    """
    Smarter API Guardrail Manifest - Status class.

    Read only. Besides ownership, it reports the guardrail's events of the last 30 days. The
    LLMClients that use it are reported in ``dependencies``.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    accountNumber: str = Field(
        description=f"{class_identifier}.account_number: The account owner of this {MANIFEST_KIND}. Read only.",
    )

    username: str = Field(
        description=f"{class_identifier}.username: The Smarter user who created this {MANIFEST_KIND}. Read only.",
    )

    triggered: Optional[int] = Field(
        default=None,
        description=f"{class_identifier}.triggered: how many times this {MANIFEST_KIND} triggered in the last 30 days. Read only.",
    )

    blocked: Optional[int] = Field(
        default=None,
        description=f"{class_identifier}.blocked: how many prompts this {MANIFEST_KIND} blocked in the last 30 days. Read only.",
    )

    errors: Optional[int] = Field(
        default=None,
        description=f"{class_identifier}.errors: how many times this {MANIFEST_KIND} failed to run in the last 30 days. Read only.",
    )

    lastTriggered: Optional[datetime.datetime] = Field(
        default=None,
        description=f"{class_identifier}.lastTriggered: when this {MANIFEST_KIND} last triggered. Read only.",
    )
