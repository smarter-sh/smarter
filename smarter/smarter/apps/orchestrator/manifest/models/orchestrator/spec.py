"""Pydantic manifest spec for the Orchestrator SAM (Smarter API Manifest) resource."""

import os
from typing import Any, ClassVar

from pydantic import BaseModel, Field, field_validator, model_validator

from smarter.apps.orchestrator.enum import HarnessRole, OrchestrationStrategy
from smarter.apps.orchestrator.manifest.models.orchestrator.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMSpecBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"

# --- Sub-blocks --------------------------------------------------------


class SAMOrchestratorHarnessConfig(BaseModel):
    """A single LLMClient (Harness) membership within the Orchestrator.

    Mirrors smarter.apps.orchestrator.models.OrchestratorHarness. The
    llmClientName is a reference by name, not by primary key — resolved
    against the account's existing LLMClients at apply time.
    """

    llmClientName: str = Field(description="Name of an existing LLMClient to attach as a Harness.")
    role: HarnessRole = HarnessRole.EXECUTOR
    executionOrder: int = Field(default=0, ge=0, description="Relative ordering for sequential/supervisor strategies.")
    isActive: bool = True
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Per-membership overrides (e.g. temperature, system prompt fragment, tool allowlist).",
    )


# --- Top-level spec ------------------------------------------------------


class SAMOrchestratorSpecConfig(BaseModel):
    """Spec block for an Orchestrator SAM manifest.

    Mirrors smarter.apps.orchestrator.models.Orchestrator. Consumed by the
    manifest controller to create/update the corresponding Orchestrator
    model instance and its OrchestratorHarness memberships.
    """

    strategy: OrchestrationStrategy = OrchestrationStrategy.SEQUENTIAL
    maxIterations: int = Field(default=10, ge=1, description="Upper bound on orchestration loop iterations.")
    isActive: bool = True
    harnesses: list[SAMOrchestratorHarnessConfig] = Field(
        ...,
        min_length=1,
        description="LLMClients (Harnesses) that participate in this Orchestrator.",
    )

    @field_validator("harnesses")
    @classmethod
    def validate_unique_llmclients(cls, v: list[SAMOrchestratorHarnessConfig]) -> list[SAMOrchestratorHarnessConfig]:
        # Mirrors the model's unique_together on (orchestrator, llmclient) —
        # the same LLMClient can't be attached to an Orchestrator twice.
        names = [harness.llmClientName for harness in v]
        duplicates = {name for name in names if names.count(name) > 1}
        if duplicates:
            raise ValueError(f"Duplicate llmClientName(s) in harnesses: {sorted(duplicates)}")
        return v

    @model_validator(mode="after")
    def validate_strategy_role_requirements(self) -> "SAMOrchestratorSpecConfig":
        roles = {harness.role for harness in self.harnesses}
        if self.strategy == OrchestrationStrategy.SUPERVISOR and HarnessRole.PLANNER not in roles:
            raise ValueError("strategy 'supervisor' requires at least one harness with role 'planner'.")
        if self.strategy == OrchestrationStrategy.ROUTER and HarnessRole.ROUTER not in roles:
            raise ValueError("strategy 'router' requires at least one harness with role 'router'.")
        if self.strategy in (OrchestrationStrategy.DEBATE, OrchestrationStrategy.VOTING) and len(self.harnesses) < 2:
            raise ValueError(f"strategy '{self.strategy.value}' requires at least two harnesses.")
        return self


class SAMOrchestratorSpec(AbstractSAMSpecBase):
    """Smarter API Orchestrator Manifest Orchestrator.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    config: SAMOrchestratorSpecConfig = Field(
        ..., description=f"{class_identifier}.config[object]. The configuration for the {MANIFEST_KIND}."
    )


__all__ = [
    "SAMOrchestratorSpec",
    "SAMOrchestratorSpecConfig",
    "SAMOrchestratorHarnessConfig",
]
