"""Smarter API Manifest - MCPClient.status."""

import datetime
import os
from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.mcpclient.manifest.models.mcpclient.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMStatusBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMMCPClientStatus(AbstractSAMStatusBase):
    """
    Smarter API MCPClient Manifest - Status class.

    Read only. Besides ownership, it reports the result of the last connection to the MCP server.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    accountNumber: str = Field(
        description=f"{class_identifier}.account_number: The account owner of this {MANIFEST_KIND}. Read only.",
    )

    username: str = Field(
        description=f"{class_identifier}.username: The Smarter user who created this {MANIFEST_KIND}. Read only.",
    )

    connectionStatus: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.connectionStatus: the result of the last connection to the MCP server: "
            "unconfigured, connected, disconnected or error. Read only."
        ),
    )

    protocolVersion: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.protocolVersion: the MCP protocol version negotiated with the server. Read only.",
    )

    serverName: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.serverName: the name that the MCP server reported. Read only.",
    )

    serverVersion: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.serverVersion: the version that the MCP server reported. Read only.",
    )

    lastConnected: Optional[datetime.datetime] = Field(
        default=None,
        description=f"{class_identifier}.lastConnected: when Smarter last connected to the MCP server. Read only.",
    )

    lastError: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.lastError: the error of the last failed connection, if any. Read only.",
    )

    tools: Optional[list[str]] = Field(
        default=None,
        description=(
            f"{class_identifier}.tools: the names of the MCP server's tools that this {MANIFEST_KIND} "
            "offers the LLM, as of the last connection. Read only."
        ),
    )
