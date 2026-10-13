"""
Pydantic models of the LLMHosts' REST api responses (``/api/v1/llmhosts/``).

The REST api's views build their responses from these models, and the Smarter api's OpenAPI
document (:mod:`smarter.apps.api.v1.contract.openapi`) publishes their JSON Schemas.

:class:`LLMHostApiLLMHost` is an LLMHost, as :class:`smarter.apps.llmhost.serializers.LLMHostSerializer`
returned it before the api was modeled, which clients already read. One value changed: its
``canDelete`` is computed for the requesting user. The other models replace the dicts that the views
and the LLMHost service built by hand, with the same keys. Their date-times now end in ``Z``, where
they ended in ``+00:00``: the same instant. A catalog's model keeps its snake_case keys.

The models forbid extra fields: the api returns exactly what they declare.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from smarter.apps.account.contract.models import (
    AccountApiModel,
    AccountApiUserProfile,
    MetaDataApiAnnotations,
)
from smarter.apps.account.serializers import user_can_delete

if TYPE_CHECKING:
    from smarter.apps.llmhost.models import LLMHost
    from smarter.apps.llmhost.services.discovery import ModelInfo
    from smarter.apps.llmhost.services.observability import LLMHostObservation


LLMHostApiModelSource = Literal["huggingface", "ollama", "s3", "url", "pvc"]
"""The choices of ``LLMHost.model_source``.

A test fails if the two differ.
"""

LLMHostApiModelTask = Literal["text-generation", "embedding"]
"""The choices of ``LLMHost.model_task``.

A test fails if the two differ.
"""

LLMHostApiQuantization = Literal["none", "fp32", "fp16", "bf16", "fp8", "mxfp4", "int8", "int4", "gguf", "awq", "gptq"]
"""The choices of ``LLMHost.quantization``.

A test fails if the two differ.
"""

LLMHostApiInferenceEngine = Literal["vllm", "tgi", "sglang", "llama_cpp", "ollama", "tei", "custom"]
"""The choices of ``LLMHost.inference_engine``.

A test fails if the two differ.
"""

LLMHostApiFormat = Literal["openai_compatible", "huggingface", "ollama_native", "custom"]
"""The choices of ``LLMHost.api_format``.

A test fails if the two differ.
"""

LLMHostApiStatusValue = Literal[
    "provisioning", "pending", "downloading", "deploying", "active", "degraded", "inactive", "error"
]
"""The choices of ``LLMHost.status``.

A test fails if the two differ.
"""


def money(value: Optional[Decimal], decimal_places: int = 4) -> Optional[str]:
    """
    A decimal amount as the api returns it: a string with the field's decimal places, e.g. ``"0.1768"``.

    :param value: The amount, or None.
    :type value: Optional[Decimal]
    :param decimal_places: The number of decimal places.
    :type decimal_places: int
    :returns: The amount, or None.
    :rtype: Optional[str]
    """
    return None if value is None else str(Decimal(value).quantize(Decimal(10) ** -decimal_places))


class LLMHostApiLLMHost(AccountApiModel):
    """A self-hosted LLM: a :class:`smarter.apps.llmhost.models.LLMHost`."""

    id: int = Field(..., description="The row's primary key.")
    hashed_id: str = Field(..., description="The LLMHost's hashed id, which its urls use.")
    created_at: Optional[datetime] = Field(None, description="TimestampedModel.created_at.")
    updated_at: Optional[datetime] = Field(None, description="TimestampedModel.updated_at.")
    name: str = Field(..., description="MetaDataModel.name, in snake_case.")
    description: Optional[str] = Field(None, description="MetaDataModel.description.")
    version: Optional[str] = Field(None, description="MetaDataModel.version, e.g. 1.0.0.")
    tags: list[str] = Field(default_factory=list, description="MetaDataModel.tags, by name.")
    annotations: MetaDataApiAnnotations = Field(None, description="MetaDataModel.annotations.")
    user_profile: AccountApiUserProfile = Field(..., description="The LLMHost's owner.")
    can_delete: bool = Field(..., description="Whether the requesting user may delete the LLMHost now.")
    manifest_url: str = Field(..., description="The url of the LLMHost's manifest in the web console.")
    spec: dict[str, JsonValue] = Field(..., description="The manifest's spec, as it was applied. See SAMLLMHost.")
    model_source: LLMHostApiModelSource = Field(..., description="Where the model's weights come from.")
    model_repository: str = Field(..., description="The model, e.g. meta-llama/Llama-3.1-8B-Instruct.")
    model_revision: str = Field(..., description="The model's revision, e.g. main.")
    model_task: LLMHostApiModelTask = Field(..., description="What the model does.")
    served_model_name: str = Field(..., description="The model's name in its api's requests.")
    license: str = Field(..., description="The model's license.")
    model_architecture: str = Field(..., description="The model's architecture.")
    parameter_count: Optional[int] = Field(None, description="The model's number of parameters.")
    context_window: Optional[int] = Field(None, description="The model's context window, in tokens.")
    quantization: LLMHostApiQuantization = Field(..., description="The weights' quantization.")
    embedding_dimensions: Optional[int] = Field(None, description="An embedding model's dimensions.")
    supports_streaming: bool
    supports_function_calling: bool
    supports_vision: bool
    supports_reasoning: bool
    inference_engine: LLMHostApiInferenceEngine = Field(..., description="The inference server.")
    api_format: LLMHostApiFormat = Field(..., description="The format of the inference server's api.")
    api_key_secret: Optional[int] = Field(None, description="The id of the Secret of its api key, if any.")
    compute: Optional[int] = Field(None, description="The id of its LLMHostCompute, if any.")
    gpu_type: str = Field(..., description="The GPU, e.g. nvidia-l4.")
    gpu_count: int = Field(..., ge=0, description="GPUs per replica.")
    vram_required_gb: Optional[int] = Field(None, description="The VRAM that the model needs.")
    replicas: int = Field(..., ge=0, description="The desired replicas.")
    cost_per_hour: Optional[str] = Field(
        None, description="The cost of a replica, per hour, in USD, as a decimal string."
    )
    status: LLMHostApiStatusValue = Field(..., description="Its deployment's status.")
    status_message: str = Field(..., description="Its status, for a person.")
    is_active: bool = Field(..., description="Whether LLMClients may use it.")
    ready_replicas: int = Field(..., ge=0, description="The ready replicas, as of the last check.")
    endpoint_url: str = Field(..., description="The base url of its api inside the cluster.")
    public_url: str = Field(..., description="The base url of its Ingress, if any.")
    health_check_url: str = Field(..., description="The url of its health check.")
    last_health_check_at: Optional[datetime] = None
    last_health_ok: Optional[bool] = None
    deployed_at: Optional[datetime] = None

    @classmethod
    def from_model(cls, llmhost: "LLMHost", user: object = None) -> "LLMHostApiLLMHost":
        """
        The contract's model of an LLMHost.

        :param llmhost: The row, whose ``user_profile`` should be fetched with it.
        :type llmhost: smarter.apps.llmhost.models.LLMHost
        :param user: The requesting user, for ``can_delete``. None may delete nothing.
        :type user: object
        :returns: The model.
        :rtype: LLMHostApiLLMHost
        """
        # pylint: disable=import-outside-toplevel
        from django.urls import reverse

        from smarter.apps.llmhost.manifest.models.llmhost.const import (
            MANIFEST_KIND as LLMHOST_KIND,
        )
        from smarter.apps.llmhost.urls import LLMHostReverseNames

        computed = {
            "id": llmhost.pk,
            "tags": [tag.name for tag in llmhost.tags.all()],
            "user_profile": AccountApiUserProfile.from_model(llmhost.user_profile),
            "can_delete": user_can_delete(llmhost, LLMHOST_KIND, user),
            "manifest_url": reverse(
                f"{LLMHostReverseNames.namespace}:{LLMHostReverseNames.detailview}",
                kwargs={"hashed_id": llmhost.hashed_id},
            ),
            "api_key_secret": llmhost.api_key_secret_id,  # type: ignore[attr-defined]
            "compute": llmhost.compute_id,  # type: ignore[attr-defined]
            "cost_per_hour": money(llmhost.cost_per_hour, llmhost._meta.get_field("cost_per_hour").decimal_places),
        }
        fields = {name: getattr(llmhost, name) for name in cls.model_fields if name not in computed}
        return cls(**fields, **computed)


class LLMHostApiPod(AccountApiModel):
    """A pod of an LLMHost: its name, phase, readiness, restarts, and why it is not ready, if it isn't."""

    name: Optional[str] = None
    phase: Optional[str] = Field(None, description="e.g. Running.")
    ready: bool
    restarts: int = Field(..., ge=0)
    downloading: bool = Field(..., description="Whether it is downloading the model's weights.")
    reason: Optional[str] = Field(None, description="Why it is not ready.")


class LLMHostApiObservation(AccountApiModel):
    """What is known about an LLMHost, as of a status check."""

    status: str = Field(..., description="The LLMHost's status, e.g. active.")
    message: str = Field("", description="Why, e.g. a container error.")
    replicas: int = Field(0, description="The desired replicas.")
    ready_replicas: int = Field(0, description="The ready replicas.")
    healthy: Optional[bool] = Field(None, description="The result of the health check, or null if not checked.")
    endpoint: Optional[str] = Field(None, description="The base url inside the cluster.")
    public_url: Optional[str] = Field(None, description="The base url of the Ingress, if any.")
    pods: list[LLMHostApiPod] = Field(default_factory=list, description="A summary of each pod.")
    checked_at: Optional[datetime] = Field(None, description="When the status was checked.")

    @classmethod
    def from_observation(cls, observation: "LLMHostObservation") -> "LLMHostApiObservation":
        """
        The contract's model of a status check.

        :param observation: The observation.
        :type observation: smarter.apps.llmhost.services.observability.LLMHostObservation
        :returns: The model.
        :rtype: LLMHostApiObservation
        """
        return cls(
            status=observation.status,
            message=observation.message,
            replicas=observation.replicas,
            ready_replicas=observation.ready_replicas,
            healthy=observation.healthy,
            endpoint=observation.endpoint,
            public_url=observation.public_url,
            pods=[LLMHostApiPod(**pod) for pod in observation.pods],
            checked_at=observation.checked_at,
        )


class LLMHostApiStatus(LLMHostApiObservation):
    """An LLMHost's status, checked now, or after a deployment: the observation, with the LLMHost's name."""

    llmhost: str = Field(..., description="The LLMHost's name.")


class LLMHostApiLogs(AccountApiModel):
    """The inference server's recent logs."""

    llmhost: str = Field(..., description="The LLMHost's name.")
    logs: str


class LLMHostApiPlan(AccountApiModel):
    """The Kubernetes resources that a deployment would apply, with secrets redacted."""

    llmhost: str = Field(..., description="The LLMHost's name.")
    resources: list[dict[str, JsonValue]] = Field(..., description="Kubernetes manifests.")


class LLMHostApiUndeployed(AccountApiModel):
    """An LLMHost whose Kubernetes resources were destroyed."""

    llmhost: str = Field(..., description="The LLMHost's name.")
    status: LLMHostApiStatusValue
    message: str


class LLMHostApiReportTotals(AccountApiModel):
    """The totals of a report of LLMHosts."""

    llmhosts: int = Field(..., ge=0)
    deployed: int = Field(..., ge=0)
    active: int = Field(..., ge=0)
    errors: int = Field(..., ge=0)
    gpus: int = Field(..., ge=0, description="The GPUs that the deployed LLMHosts use.")
    cost_per_hour: str = Field(..., description="The deployed LLMHosts' cost per hour, in USD, as a decimal string.")
    estimated_cost: str = Field(..., description="Their estimated cost so far, in USD, as a decimal string.")


class LLMHostApiReportHost(AccountApiModel):
    """An LLMHost in a report: its status, model, GPUs and cost."""

    name: str
    owner: str = Field(..., description="The owner's username.")
    status: str
    engine: str
    model: str
    task: str
    replicas: int
    ready_replicas: int
    compute: Optional[str] = Field(None, description="Its LLMHostCompute's name, if any.")
    gpus: int
    gpu_type: Optional[str] = None
    endpoint: Optional[str] = None
    public_url: Optional[str] = None
    deployed_at: Optional[datetime] = None
    uptime_hours: Optional[float] = None
    cost_per_hour: Optional[str] = Field(None, description="Its cost per hour, in USD, as a decimal string.")
    estimated_cost: Optional[str] = Field(None, description="Its estimated cost so far, in USD, as a decimal string.")


class LLMHostApiReport(AccountApiModel):
    """A summary of LLMHosts: their count by status and engine, the GPUs they use, and their cost."""

    totals: LLMHostApiReportTotals
    by_status: dict[str, int] = Field(..., description="The number of LLMHosts of each status.")
    by_engine: dict[str, int] = Field(..., description="The number of LLMHosts of each inference engine.")
    llmhosts: list[LLMHostApiReportHost]


class LLMHostApiCatalogModel(BaseModel):
    """
    A model, as a catalog, e.g. Hugging Face, describes it.

    Its keys are snake_case, e.g. ``parameter_count``, as the api returned them before it was modeled.
    """

    model_config = ConfigDict(extra="forbid")

    catalog: str = Field(..., description="The catalog, e.g. huggingface or builtin.")
    source: str = Field(..., description="Where its weights come from.")
    repository: str = Field(..., description="The model, e.g. meta-llama/Llama-3.1-8B-Instruct.")
    task: str
    description: Optional[str] = None
    license: Optional[str] = None
    gated: bool = Field(False, description="Whether downloading it needs an accepted license and a token.")
    architecture: Optional[str] = None
    parameter_count: Optional[int] = None
    context_window: Optional[int] = None
    quantization: str = "none"
    downloads: Optional[int] = None
    likes: Optional[int] = None
    tags: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    manifest: Optional[dict[str, JsonValue]] = Field(None, description="A ready-made manifest, for built-in models.")

    @classmethod
    def from_model_info(cls, model: "ModelInfo") -> "LLMHostApiCatalogModel":
        """
        The contract's model of a catalog's model.

        :param model: The model.
        :type model: smarter.apps.llmhost.services.discovery.ModelInfo
        :returns: The model.
        :rtype: LLMHostApiCatalogModel
        """
        return cls(**{name: getattr(model, name) for name in cls.model_fields})


class LLMHostApiDiscovery(AccountApiModel):
    """The models of a catalog that match a search, most popular first."""

    models: list[LLMHostApiCatalogModel]


class LLMHostApiDraftManifest(AccountApiModel):
    """A draft LLMHost manifest for a model, to review and apply."""

    manifest: dict[str, JsonValue] = Field(..., description="The draft manifest. See SAMLLMHost.")


LLMHOST_API_MODELS = (
    LLMHostApiLLMHost,
    LLMHostApiStatus,
    LLMHostApiLogs,
    LLMHostApiPlan,
    LLMHostApiUndeployed,
    LLMHostApiReport,
    LLMHostApiDiscovery,
    LLMHostApiDraftManifest,
)
"""The models whose JSON Schemas the Smarter api's OpenAPI document includes.

Their dependencies are included with them.
"""

__all__ = [
    "LLMHOST_API_MODELS",
    "LLMHostApiCatalogModel",
    "LLMHostApiDiscovery",
    "LLMHostApiDraftManifest",
    "LLMHostApiFormat",
    "LLMHostApiInferenceEngine",
    "LLMHostApiLLMHost",
    "LLMHostApiLogs",
    "LLMHostApiModelSource",
    "LLMHostApiModelTask",
    "LLMHostApiObservation",
    "LLMHostApiPlan",
    "LLMHostApiPod",
    "LLMHostApiQuantization",
    "LLMHostApiReport",
    "LLMHostApiReportHost",
    "LLMHostApiReportTotals",
    "LLMHostApiStatus",
    "LLMHostApiStatusValue",
    "LLMHostApiUndeployed",
    "money",
]
