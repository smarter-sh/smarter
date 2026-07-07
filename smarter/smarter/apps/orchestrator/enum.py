"""Enums for the Orchestrator SAM (Smarter API Manifest) resource.

Mirrors smarter.apps.llmhost.enum: plain str Enums for the Pydantic
manifest layer, kept separate from (but value-aligned with) the Django
TextChoices on smarter.apps.orchestrator.models.
"""

from enum import Enum


class OrchestrationStrategy(str, Enum):
    """Coordination pattern the Orchestrator applies across its member LLMClients.

    Values must stay aligned with
    smarter.apps.orchestrator.models.OrchestrationStrategy.
    """

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    SUPERVISOR = "supervisor"
    ROUTER = "router"
    VOTING = "voting"
    DEBATE = "debate"


class HarnessRole(str, Enum):
    """Role an LLMClient (Harness) plays within an Orchestrator.

    Values must stay aligned with
    smarter.apps.orchestrator.models.OrchestratorHarness.Role.
    """

    PLANNER = "planner"
    EXECUTOR = "executor"
    CRITIC = "critic"
    ROUTER = "router"
    SUMMARIZER = "summarizer"
    TOOL_CALLER = "tool_caller"


__all__ = ["OrchestrationStrategy", "HarnessRole"]
