"""
Smarter API Manifest - Budget.spec.

A Budget is a set of spending limits. It is enforced on each of the resources in its
``spec.resources``: when a resource's spending reaches a limit, further charges to it are
refused, e.g. a prompt is answered with the budget's message instead of calling the LLM.

.. code-block:: yaml

    spec:
      config:
        unit: cost              # cost, in USD, or tokens
        period: month           # the billing period of periodicLimit: hour, day, week or month
        periodicLimit: 10.00    # the most that may be spent in a billing period. 0 means no limit.
        absoluteLimit: 100.00   # the most that may be spent in total. 0 means no limit.
        duration: 0             # billing periods after which the budget no longer applies. 0 means never.
        action: block           # block further charges, or warn only
        warningThreshold: 80    # the percentage of a limit at which a warning is sent. 0 means never.
        message: "You have used this month's AI allowance. It renews on the 1st."
      resources:
        - kind: User
          name: student1
        - kind: LLMClient
          name: stackademy_sql
          accountNumber: "3141-5926-5359"   # optional. Defaults to your own account.
        - recordLocator: provider-rc2x       # any resource, by its record locator

Spending is counted from when the budget is attached to a resource. Cost is priced with
LLMPrices, in USD per million tokens, and LLMHostCompute nodes with their price per hour.
"""

import os
from decimal import Decimal
from typing import ClassVar, Literal, Optional

from pydantic import Field, model_validator

from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase, SmarterBasePydanticModel

from .const import (
    DEFAULT_WARNING_THRESHOLD,
    MANIFEST_KIND,
    MAX_MESSAGE_LENGTH,
    MAX_RESOURCES,
)

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"

RESOURCE_KINDS = (
    "Account",
    "User",
    "ApiConnection",
    "SqlConnection",
    "LLMClient",
    "LLMHost",
    "LLMHostCompute",
    "MCPClient",
    "Orchestrator",
    "Provider",
    "Proxy",
    "Vectorsearch",
    "ApiPlugin",
    "SkillPlugin",
    "SqlPlugin",
    "StaticPlugin",
    "WebsearchPlugin",
)
"""The kinds of resource that a budget can be attached to by kind and name."""


class SAMBudgetSpecConfig(SmarterBasePydanticModel):
    """Smarter API Budget Manifest Budget.spec.config: the budget's limits."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".config"

    unit: Literal["cost", "tokens"] = Field(
        default="cost", description=f"{class_identifier}.unit: what the limits measure: cost in USD, or total tokens."
    )
    period: Literal["hour", "day", "week", "month"] = Field(
        default="month",
        description=f"{class_identifier}.period: the billing period of periodicLimit and duration.",
    )
    periodicLimit: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description=f"{class_identifier}.periodicLimit: the most that may be spent in a billing period. 0 means no limit.",
    )
    absoluteLimit: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description=f"{class_identifier}.absoluteLimit: the most that may be spent in total, from when the budget is attached. 0 means no limit.",
    )
    duration: int = Field(
        default=0,
        ge=0,
        description=f"{class_identifier}.duration: the billing periods, from when the budget is attached, after which it no longer applies. 0 means never.",
    )
    action: Literal["block", "warn"] = Field(
        default="block",
        description=f"{class_identifier}.action: block further charges when a limit is reached, or only warn.",
    )
    warningThreshold: int = Field(
        default=DEFAULT_WARNING_THRESHOLD,
        ge=0,
        le=100,
        description=f"{class_identifier}.warningThreshold: the percentage of a limit at which a warning is sent. 0 means never.",
    )
    message: Optional[str] = Field(
        default=None,
        max_length=MAX_MESSAGE_LENGTH,
        description=f"{class_identifier}.message: what people are told when the budget blocks their request. Defaults to a description of the limit that was reached.",
    )


class SAMBudgetSpecResource(SmarterBasePydanticModel):
    """
    Smarter API Budget Manifest Budget.spec.resources[]: a resource that the budget is enforced on.

    Either kind and name, with an optional accountNumber, or a recordLocator.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".resources"

    kind: Optional[Literal[RESOURCE_KINDS]] = Field(  # type: ignore[valid-type]
        default=None, description=f"{class_identifier}.kind: the resource's manifest kind, e.g. LLMClient."
    )
    name: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.name: the resource's name. For an Account, its account number; for a User, the username.",
    )
    accountNumber: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.accountNumber: the account that the resource belongs to. Defaults to your own.",
    )
    recordLocator: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.recordLocator: any resource's record locator, e.g. llmclient-rc2x, in place of kind and name.",
    )

    @model_validator(mode="after")
    def validate_identity(self) -> "SAMBudgetSpecResource":
        """Either a kind and a name, or a recordLocator."""
        if self.recordLocator:
            if self.kind or self.name:
                raise SAMValidationError("resources: give either kind and name, or recordLocator, not both.")
        elif not (self.kind and self.name):
            raise SAMValidationError("resources: kind and name, or recordLocator, are required.")
        return self


class SAMBudgetSpec(AbstractSAMSpecBase):
    """Smarter API Budget Manifest Budget.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    config: SAMBudgetSpecConfig = Field(
        ..., description=f"{class_identifier}.config[object]. The limits of the {MANIFEST_KIND}."
    )
    resources: list[SAMBudgetSpecResource] = Field(
        default_factory=list,
        max_length=MAX_RESOURCES,
        description=f"{class_identifier}.resources[list]. The resources that the {MANIFEST_KIND} is enforced on. Resources that are removed from the list are detached.",
    )
