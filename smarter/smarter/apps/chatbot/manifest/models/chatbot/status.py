"""Smarter API Manifest - Plugin.status"""

import os
from datetime import datetime
from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.chatbot.manifest.models.chatbot.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMStatusBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMChatbotStatus(AbstractSAMStatusBase):
    """Smarter API Chatbot Manifest - Status class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    accountNumber: str = Field(
        description=f"{class_identifier}.account_number: The account owner of this {MANIFEST_KIND}. Read only.",
    )

    username: str = Field(
        description=f"{class_identifier}.username: The Smarter user who created this {MANIFEST_KIND}. Read only.",
    )

    created: datetime = Field(
        description=f"{class_identifier}.created: The date in which this {MANIFEST_KIND} was created. Read only.",
    )

    modified: datetime = Field(
        description=f"{class_identifier}.modified: The date in which this {MANIFEST_KIND} was most recently changed. Read only.",
    )
    deployed: bool = Field(
        description=f"{class_identifier}.deployed: Whether this {MANIFEST_KIND} is currently deployed. Read only.",
    )
    defaultHost: str = Field(
        description=f"{class_identifier}.defaultHost: The default host URL for this {MANIFEST_KIND}. Read only.",
    )
    defaultUrl: str = Field(
        description=f"{class_identifier}.defaultUrl: The default URL for this {MANIFEST_KIND}. Read only.",
    )
    customUrl: Optional[str] = Field(
        description=f"{class_identifier}.customUrl: The custom URL for this {MANIFEST_KIND}. Read only.",
    )
    sandboxHost: str = Field(
        description=f"{class_identifier}.sandboxHost: The sandbox host URL for this {MANIFEST_KIND}. Read only.",
    )
    sandboxUrl: str = Field(
        description=f"{class_identifier}.sandboxUrl: The sandbox URL for this {MANIFEST_KIND}. Read only.",
    )
    hostname: str = Field(
        description=f"{class_identifier}.hostname: The hostname for this {MANIFEST_KIND}. Read only.",
    )
    url: str = Field(
        description=f"{class_identifier}.url: The URL for this {MANIFEST_KIND}. Read only.",
    )
    urlChatbot: str = Field(
        description=f"{class_identifier}.urlChatbot: The chatbot URL for this {MANIFEST_KIND}. Read only.",
    )
    urlChatapp: str = Field(
        description=f"{class_identifier}.urlChatapp: The chatapp URL for this {MANIFEST_KIND}. Read only.",
    )
    urlChatConfig: str = Field(
        description=f"{class_identifier}.urlChatConfig: The chat config URL for this {MANIFEST_KIND}. Read only.",
    )
    dnsVerificationStatus: str = Field(
        description=f"{class_identifier}.dnsVerificationStatus: The DNS verification status for this {MANIFEST_KIND}. Read only.",
    )
