"""Smarter API Prompt - Prompt.spec."""

import os
from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.prompt.manifest.models.prompt.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMSpecBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMPromptSpecConfig(AbstractSAMSpecBase):
    """Smarter API Prompt Manifest Prompt.spec.config."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".configuration"

    sessionKey: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.sessionKey[str]. Read only. The session key of the {MANIFEST_KIND}'s chat session.",
    )
    llmclient: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.llmclient[str]. Read only. The name of the LLMClient of the chat session.",
    )
    ipAddress: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.ipAddress[str]. Read only. The IP address of the client that started the chat session.",
    )
    userAgent: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.userAgent[str]. Read only. The user agent of the client that started the chat session.",
    )
    url: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.url[str]. Read only. The url at which the chat session was started.",
    )
