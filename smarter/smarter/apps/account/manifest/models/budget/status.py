"""Smarter API Manifest - Budget.status."""

import datetime
import os
from decimal import Decimal
from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.account.manifest.models.budget.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMStatusBase, SmarterBasePydanticModel

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMBudgetStatusResource(SmarterBasePydanticModel):
    """The budget versus the actual spending of one of the budget's resources.

    Read only.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".resources"

    recordLocator: str = Field(description=f"{class_identifier}.recordLocator: the resource's record locator.")
    isActive: bool = Field(description=f"{class_identifier}.isActive: whether the budget is enforced on it.")
    startDate: datetime.datetime = Field(description=f"{class_identifier}.startDate: when the budget was attached.")
    expiresAt: Optional[datetime.datetime] = Field(
        default=None, description=f"{class_identifier}.expiresAt: when the budget's duration ends."
    )
    periodicActual: Decimal = Field(description=f"{class_identifier}.periodicActual: spending this billing period.")
    periodicPercent: Optional[float] = Field(
        default=None, description=f"{class_identifier}.periodicPercent: periodicActual, as a percentage of the limit."
    )
    absoluteActual: Decimal = Field(description=f"{class_identifier}.absoluteActual: spending since startDate.")
    absolutePercent: Optional[float] = Field(
        default=None, description=f"{class_identifier}.absolutePercent: absoluteActual, as a percentage of the limit."
    )
    isLocked: bool = Field(description=f"{class_identifier}.isLocked: whether the budget refuses further charges.")
    lockReason: Optional[str] = Field(
        default=None, description=f"{class_identifier}.lockReason: which limit was reached."
    )


class SAMBudgetStatus(AbstractSAMStatusBase):
    """Smarter API Budget Manifest - Status class.

    Read only.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    resources: list[SAMBudgetStatusResource] = Field(
        default_factory=list,
        description=f"{class_identifier}.resources: the budget versus the actual spending of each resource. Read only.",
    )
