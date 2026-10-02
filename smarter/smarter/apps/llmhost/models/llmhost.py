"""
LLMHost models.

- :class:`LLMHost`: a large language model that Smarter hosts on Kubernetes, configured by
  an LLMHost manifest.
- :class:`LLMHostEvent`: a record of an LLMHost's lifecycle, for observability and reporting.
- :class:`~smarter.apps.llmhost.models.compute.LLMHostCompute`: the kind of node, and node group,
  that an LLMHost runs on.

The manifest's ``spec`` is stored, as it is, in :attr:`LLMHost.spec`, which is the source of
truth for launching the LLMHost. The other fields are copies of the parts of the spec that
are queried and reported on, e.g. the engine and the GPU count, and of the LLMHost's
observed state, e.g. its status and endpoint.
"""

import datetime
from decimal import Decimal
from typing import Any, Optional

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from smarter.apps.account.models import (
    MetaDataWithOwnershipModel,
)
from smarter.apps.llmhost.manifest.enum import (
    SAMLLMHostApiFormat,
    SAMLLMHostEngine,
    SAMLLMHostEventType,
    SAMLLMHostModelSource,
    SAMLLMHostQuantization,
    SAMLLMHostStatusEnum,
    SAMLLMHostTask,
)
from smarter.lib import logging
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_HOST_LOGGING])


def choices(enum) -> list[tuple[str, str]]:
    """Django choices from a SmarterEnumAbstract."""
    return [(value, value) for value in enum.all()]


class LLMHost(MetaDataWithOwnershipModel):
    """
    A large language model that Smarter hosts on Kubernetes.

    Distinct from an LLM Provider, which is a third-party API: the account owns the
    LLMHost's deployment lifecycle, i.e. launch, observe and destroy, through
    :class:`smarter.apps.llmhost.services.LLMHostService`.
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "LLMHosts"
        unique_together = ("user_profile", "name")

    # --- the manifest's spec, as it is -----------------------------------
    spec = models.JSONField(
        default=dict,
        blank=True,
        help_text="The manifest's spec, in camelCase. The source of truth for launching the LLMHost.",
    )

    # --- model -------------------------------------------------------------
    model_source = models.CharField(
        max_length=20, choices=choices(SAMLLMHostModelSource), default=SAMLLMHostModelSource.HUGGINGFACE.value
    )
    model_repository = models.CharField(
        max_length=255,
        blank=True,
        help_text="e.g. 'meta-llama/Llama-3.1-8B-Instruct', 'llama3.1:8b' or 's3://bucket/prefix'",
    )
    model_revision = models.CharField(
        max_length=64,
        blank=True,
        help_text="Commit SHA, branch or tag pinned for reproducible deploys.",
    )
    model_task = models.CharField(
        max_length=20, choices=choices(SAMLLMHostTask), default=SAMLLMHostTask.TEXT_GENERATION.value
    )
    served_model_name = models.CharField(
        max_length=255, blank=True, help_text="The model name that clients send in their requests."
    )
    license = models.CharField(max_length=100, blank=True)
    model_architecture = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. 'llama', 'mistral', 'qwen3'",
    )
    parameter_count = models.BigIntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    context_window = models.PositiveIntegerField(null=True, blank=True)
    quantization = models.CharField(
        max_length=20, choices=choices(SAMLLMHostQuantization), default=SAMLLMHostQuantization.NONE.value
    )
    embedding_dimensions = models.PositiveIntegerField(
        null=True, blank=True, help_text="Set only for embedding models."
    )
    supports_streaming = models.BooleanField(default=True)
    supports_function_calling = models.BooleanField(default=False)
    supports_vision = models.BooleanField(default=False)
    supports_reasoning = models.BooleanField(default=False)

    # --- serving -------------------------------------------------------------
    inference_engine = models.CharField(
        max_length=20, choices=choices(SAMLLMHostEngine), default=SAMLLMHostEngine.VLLM.value
    )
    api_format = models.CharField(
        max_length=20, choices=choices(SAMLLMHostApiFormat), default=SAMLLMHostApiFormat.OPENAI_COMPATIBLE.value
    )
    api_key_secret = models.ForeignKey(
        "secret.Secret",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="llmhosts",
        help_text="The Smarter Secret with the API key that clients send as a Bearer token.",
    )

    # --- infrastructure ------------------------------------------------------
    compute = models.ForeignKey(
        "llmhost.LLMHostCompute",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="llmhosts",
        help_text="The kind of node, and node group, that the LLMHost runs on: spec.compute.",
    )
    gpu_type = models.CharField(max_length=50, blank=True, help_text="e.g. 'A10G'")
    gpu_count = models.PositiveSmallIntegerField(default=0, help_text="GPUs per replica.")
    vram_required_gb = models.PositiveIntegerField(null=True, blank=True)
    replicas = models.PositiveSmallIntegerField(default=1)
    cost_per_hour = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="The cost per hour of one replica: its share of its compute's node.",
    )

    # --- observed state ------------------------------------------------------
    status = models.CharField(
        max_length=20,
        choices=choices(SAMLLMHostStatusEnum),
        default=SAMLLMHostStatusEnum.INACTIVE.value,
        db_index=True,
    )
    status_message = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    ready_replicas = models.PositiveSmallIntegerField(default=0)
    endpoint_url = models.URLField(blank=True, help_text="The base URL inside the cluster.")
    public_url = models.URLField(blank=True, help_text="The base URL of the Ingress, if any.")
    health_check_url = models.URLField(blank=True)
    last_health_check_at = models.DateTimeField(null=True, blank=True)
    last_health_ok = models.BooleanField(null=True, blank=True)
    deployed_at = models.DateTimeField(null=True, blank=True, help_text="When the LLMHost was last launched.")

    def __str__(self) -> str:
        return f"{self.name}"

    @property
    def is_deployed(self) -> bool:
        """Whether the LLMHost's Kubernetes resources exist, as of the last status check."""
        return self.status in SAMLLMHostStatusEnum.deployed()

    @property
    def uptime(self) -> Optional[datetime.timedelta]:
        """The time since the LLMHost was launched, if it is deployed."""
        if not self.deployed_at or not self.is_deployed:
            return None
        return timezone.now() - self.deployed_at

    @property
    def uptime_hours(self) -> Optional[float]:
        uptime = self.uptime
        return round(uptime.total_seconds() / 3600, 4) if uptime is not None else None

    @property
    def estimated_cost(self) -> Optional[Decimal]:
        """The cost since the LLMHost was launched: uptime times replicas times cost_per_hour."""
        hours = self.uptime_hours
        if hours is None or self.cost_per_hour is None:
            return None
        return (Decimal(str(hours)) * self.replicas * self.cost_per_hour).quantize(Decimal("0.0001"))

    def record_event(
        self, event_type: str, message: str = "", details: Optional[dict[str, Any]] = None
    ) -> "LLMHostEvent":
        """Record a lifecycle event, with the LLMHost's current status."""
        return LLMHostEvent.objects.create(
            llmhost=self,
            llmhost_name=self.name,
            event_type=event_type,
            status=self.status,
            message=message or "",
            details=details or {},
        )


class LLMHostEvent(TimestampedModel):
    """
    A lifecycle event of an LLMHost: launched, status changed, destroyed, or an error.

    Events are the LLMHost's audit trail, and the basis of uptime and cost reporting.
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "LLMHost Events"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["llmhost", "event_type"])]

    llmhost = models.ForeignKey(LLMHost, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    llmhost_name = models.CharField(max_length=255, help_text="The LLMHost's name, in case it is deleted.")
    event_type = models.CharField(max_length=20, choices=choices(SAMLLMHostEventType))
    status = models.CharField(max_length=20, choices=choices(SAMLLMHostStatusEnum))
    message = models.TextField(blank=True, default="")
    details = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return f"{self.llmhost_name} {self.event_type} {self.status}"


__all__ = ["LLMHost", "LLMHostEvent"]
