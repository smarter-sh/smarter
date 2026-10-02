"""Smarter API Budget Manifest."""

from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.account.manifest.models.budget.const import MANIFEST_KIND
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.models import AbstractSAMBase

from .metadata import SAMBudgetMetadata
from .spec import SAMBudgetSpec
from .status import SAMBudgetStatus

MODULE_IDENTIFIER = MANIFEST_KIND


class SAMBudget(AbstractSAMBase):
    """Smarter API Manifest - Budget."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    metadata: SAMBudgetMetadata = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.METADATA.value}[obj]: Required, the {MANIFEST_KIND} metadata.",
    )
    spec: SAMBudgetSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
    status: Optional[SAMBudgetStatus] = Field(
        default=None,
        description=f"{class_identifier}.{SAMKeys.STATUS.value}[obj]: Optional, Read-only. Stateful status information about the {MANIFEST_KIND}.",
    )
