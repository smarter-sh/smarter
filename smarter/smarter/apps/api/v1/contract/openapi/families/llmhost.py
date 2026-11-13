"""The LLMHosts' REST reads, model discovery and deployment, under ``/api/v1/llmhosts/``."""

from smarter_types import SAMKinds

from smarter.apps.api.v1.contract.models import OpenApiPathItem
from smarter.apps.api.v1.contract.openapi.builders import (
    READ_PERMISSION,
    ApiFamily,
    id_or_hashed_id,
    query,
    rest_operation,
    rest_read,
)
from smarter.apps.llmhost.const import namespace
from smarter.apps.llmhost.contract.models import (
    LLMHostApiDiscovery,
    LLMHostApiDraftManifest,
    LLMHostApiLLMHost,
    LLMHostApiLogs,
    LLMHostApiPlan,
    LLMHostApiReport,
    LLMHostApiStatus,
    LLMHostApiUndeployed,
)

LLMHOSTS = ApiFamily(
    name=namespace,
    resource=SAMKinds.LLM_HOST.value,
    urlconf="smarter.apps.llmhost.api.v1.urls",
    description="The {plural}' REST reads, model discovery, and deployment.",
)
"""The LLMHosts' family."""


def llmhost_paths() -> dict[str, OpenApiPathItem]:
    """
    The LLMHosts' REST reads, discovery and deployment, relative to the server's ``/api/v1``.

    :returns: The paths, e.g. ``{"/llmhosts/": ...}``.
    :rtype: dict[str, OpenApiPathItem]
    """
    family = LLMHOSTS
    resource = family.resource
    llmhost_id = id_or_hashed_id(resource)
    tag = family.tag
    owner = f"Only the {resource}'s owner may call it."

    def read(operation_id, summary, description, item, parameters, note=READ_PERMISSION, many=False):
        return rest_read(operation_id, summary, description, tag, item, many=many, parameters=parameters, note=note)

    return {
        family.path(): OpenApiPathItem(
            get=read(
                family.operation_id("list"),
                f"List {family.plural}",
                f"The {family.plural} that the user may read, by name.",
                LLMHostApiLLMHost.__name__,
                [],
                many=True,
            )
        ),
        family.path("report/"): OpenApiPathItem(
            get=read(
                family.operation_id("report"),
                f"A report of {family.plural}",
                f"A summary of the {family.plural} that the user owns: their status, GPUs and cost.",
                LLMHostApiReport.__name__,
                [],
            )
        ),
        family.path("discover/"): OpenApiPathItem(
            get=read(
                family.operation_id("discover"),
                "Search a model catalog",
                "Search a model catalog, most popular first, to choose a model to host.",
                LLMHostApiDiscovery.__name__,
                [
                    query("q", "The text to search for.", {"type": "string"}),
                    query(
                        "task",
                        "Only models of this task.",
                        {"type": "string", "enum": ["text-generation", "embedding"]},
                    ),
                    query(
                        "catalog",
                        "The catalog.",
                        {"type": "string", "enum": ["huggingface", "builtin"], "default": "huggingface"},
                    ),
                    query("limit", "The number of models, at most 50.", {"type": "integer", "default": 20}),
                ],
            )
        ),
        family.path("discover/manifest/"): OpenApiPathItem(
            get=read(
                family.operation_id("discover_manifest"),
                f"Draft {family.a} manifest",
                f"Draft {family.a} manifest for a model of a catalog, to review and apply.",
                LLMHostApiDraftManifest.__name__,
                [
                    query("repository", "The model, e.g. meta-llama/Llama-3.1-8B-Instruct.", {"type": "string"}, True),
                    query("catalog", "The catalog.", {"type": "string", "default": "huggingface"}),
                    query("engine", "The inference engine, e.g. vllm.", {"type": "string"}),
                    query("name", f"The {resource}'s name.", {"type": "string"}),
                    query("tokenSecret", "The name of the Secret of a token for gated models.", {"type": "string"}),
                ],
            )
        ),
        family.path("{id}/"): OpenApiPathItem(
            get=read(
                family.operation_id("retrieve"),
                family.a_capitalized,
                f"{family.a_capitalized} that the user may read.",
                LLMHostApiLLMHost.__name__,
                [llmhost_id],
            )
        ),
        family.path("{id}/status/"): OpenApiPathItem(
            get=read(
                family.operation_id("status"),
                f"{family.a_capitalized}'s status",
                f"Check {family.a}'s status now, with its pods and health check.",
                LLMHostApiStatus.__name__,
                [llmhost_id],
            )
        ),
        family.path("{id}/logs/"): OpenApiPathItem(
            get=read(
                family.operation_id("logs"),
                f"{family.a_capitalized}'s logs",
                "The inference server's recent logs.",
                LLMHostApiLogs.__name__,
                [llmhost_id, query("tail", "The number of lines.", {"type": "integer", "default": 200})],
                note=owner,
            )
        ),
        family.path("{id}/plan/"): OpenApiPathItem(
            get=read(
                family.operation_id("plan"),
                f"{family.a_capitalized}'s deployment plan",
                "The Kubernetes resources that a deployment would apply, with secrets redacted.",
                LLMHostApiPlan.__name__,
                [llmhost_id],
                note=owner,
            )
        ),
        family.path("{id}/deploy/"): OpenApiPathItem(
            post=rest_operation(
                family.operation_id("deploy"),
                f"Deploy {family.a}",
                f"Launch the {resource}'s inference server on the platform's Kubernetes cluster. It creates billable "
                f"infrastructure, e.g. GPU nodes, and returns before the server is ready. {owner}",
                tag,
                LLMHostApiStatus.__name__,
                parameters=[llmhost_id],
                status="202",
            )
        ),
        family.path("{id}/undeploy/"): OpenApiPathItem(
            post=rest_operation(
                family.operation_id("undeploy"),
                f"Undeploy {family.a}",
                f"Destroy the {resource}'s Kubernetes resources. The {resource} remains. {owner}",
                tag,
                LLMHostApiUndeployed.__name__,
                parameters=[
                    llmhost_id,
                    query(
                        "purge",
                        "true also deletes the model volume, and the weights cached on it.",
                        {"type": "string", "enum": ["true", "false"], "default": "false"},
                    ),
                ],
            )
        ),
    }


__all__ = ["LLMHOSTS", "llmhost_paths"]
