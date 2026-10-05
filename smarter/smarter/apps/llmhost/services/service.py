"""
The LLMHost service: the lifecycle of the models that Smarter hosts on Kubernetes.

:class:`LLMHostService` is the API that the manifest broker, Celery tasks, views and
management commands use. It covers:

- **discovery**: :meth:`~LLMHostService.search_models`, :meth:`~LLMHostService.get_model` and
  :meth:`~LLMHostService.draft_manifest`, from pluggable model catalogs.
- **launch**: :meth:`~LLMHostService.plan` previews, and :meth:`~LLMHostService.launch` applies,
  an LLMHost's Kubernetes resources, and adds a node to its compute's node group if it needs one.
- **observability**: :meth:`~LLMHostService.observe` checks an LLMHost's status and health,
  :meth:`~LLMHostService.logs` returns its server's logs, and :meth:`~LLMHostService.report`
  summarizes LLMHosts' status, GPUs and cost.
- **destruction**: :meth:`~LLMHostService.destroy` deletes an LLMHost's Kubernetes resources,
  and removes its node if no other LLMHost uses it, and :meth:`~LLMHostService.delete` deletes the
  LLMHost itself.

Example::

    from smarter.apps.llmhost.services import LLMHostService

    service = LLMHostService()
    service.launch(llmhost)
    observation = service.observe(llmhost)
    print(observation.status, observation.endpoint)
    service.destroy(llmhost)
"""

import secrets
from typing import Any, Iterable, Optional

from django.utils import timezone
from pydantic import ValidationError

from smarter.apps.account.models import (
    SmarterBudgetExceeded,
    UserProfile,
    charge_authorization,
)
from smarter.apps.llmhost.const import (
    API_KEY_BYTES,
    API_KEY_SECRET_NAME,
    DEFAULT_LOG_LINES,
    MANAGED_KINDS,
    MAX_LOG_LINES,
    VOLUME_KIND,
)
from smarter.apps.llmhost.manifest.enum import SAMLLMHostEventType, SAMLLMHostStatusEnum
from smarter.apps.llmhost.manifest.models.llmhost.spec import SAMLLMHostSpec
from smarter.apps.llmhost.models import LLMHost, LLMHostCompute
from smarter.apps.llmhost.models.compute import (
    LLMHostComputeNodeGroupStatus as NodeGroupStatus,
)
from smarter.apps.llmhost.signals import (
    llmhost_destroyed,
    llmhost_launch_failed,
    llmhost_launched,
    llmhost_status_changed,
)
from smarter.apps.secret.models import Secret
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.manifest.exceptions import SAMValidationError

from .cluster import ClusterBackend, get_cluster
from .compute import ComputeProvisioner, ComputeState, computes_for, resolve_compute
from .discovery import ModelInfo, draft_manifest, get_catalog
from .engines import get_engine
from .exceptions import (
    LLMHostBudgetExceeded,
    LLMHostClusterError,
    LLMHostComputeError,
    LLMHostConfigurationError,
)
from .observability import (
    HealthProber,
    LLMHostObservation,
    build_report,
    interpret,
    summarize_pod,
)
from .renderer import (
    CONTAINER_NAME,
    RenderContext,
    label_selector,
    render_resources,
    resource_name,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_HOST_LOGGING])
logger_prefix = logging.formatted_text(f"{__name__}.LLMHostService")

Status = SAMLLMHostStatusEnum
EventType = SAMLLMHostEventType
REDACTED = "**redacted**"


class LLMHostService:
    """
    The lifecycle of LLMHosts: discover, launch, observe and destroy.

    :param cluster: The Kubernetes cluster. Defaults to :func:`~smarter.apps.llmhost.services.cluster.get_cluster`.
    :param prober: The health checker. Defaults to a :class:`HealthProber`, which only probes inside the cluster.
    :param provisioner: The nodes of LLMHosts' compute. Defaults to a :class:`ComputeProvisioner` of the cluster.
    """

    def __init__(
        self,
        cluster: Optional[ClusterBackend] = None,
        prober: Optional[HealthProber] = None,
        provisioner: Optional[ComputeProvisioner] = None,
    ):
        self._cluster = cluster
        self.prober = prober or HealthProber()
        self._provisioner = provisioner

    @property
    def cluster(self) -> ClusterBackend:
        if self._cluster is None:
            self._cluster = get_cluster()
        return self._cluster

    @property
    def provisioner(self) -> ComputeProvisioner:
        if self._provisioner is None:
            self._provisioner = ComputeProvisioner(cluster=self.cluster)
        return self._provisioner

    # --- discovery ----------------------------------------------------------------

    def search_models(
        self, query: Optional[str] = None, task: Optional[str] = None, catalog: str = "huggingface", limit: int = 20
    ) -> list[ModelInfo]:
        """Search a model catalog, most popular first."""
        return get_catalog(catalog).search(query=query, task=task, limit=limit)

    def get_model(self, repository: str, catalog: str = "huggingface") -> ModelInfo:
        """Return a model's details from a catalog."""
        return get_catalog(catalog).get(repository)

    def draft_manifest(
        self,
        repository: str,
        catalog: str = "huggingface",
        engine: Optional[str] = None,
        name: Optional[str] = None,
        token_secret: Optional[str] = None,
        user_profile: Optional[UserProfile] = None,
    ) -> dict[str, Any]:
        """
        Draft an LLMHost manifest for a model in a catalog, sized for its GPU memory.

        :param user_profile: Choose from the LLMHostComputes that this user may read. Defaults to the built-in ones.
        """
        computes = computes_for(user_profile) if user_profile is not None else None
        return draft_manifest(
            self.get_model(repository, catalog), engine=engine, name=name, token_secret=token_secret, computes=computes
        )

    # --- helpers -----------------------------------------------------------------

    @staticmethod
    def spec_of(llmhost: LLMHost) -> SAMLLMHostSpec:
        """The LLMHost's spec.

        Raises LLMHostConfigurationError if it is not valid.
        """
        try:
            return SAMLLMHostSpec(**(llmhost.spec or {}))
        except (ValidationError, SAMValidationError, TypeError) as e:
            raise LLMHostConfigurationError(f"LLMHost {llmhost.name} has an invalid spec: {e}") from e

    @staticmethod
    def base_name(llmhost: LLMHost) -> str:
        """The base name of the LLMHost's Kubernetes resources."""
        if llmhost.pk is None:
            raise LLMHostConfigurationError(f"LLMHost {llmhost.name} must be saved first.")
        return resource_name(llmhost.pk, llmhost.name)

    @staticmethod
    def default_hostname(llmhost: LLMHost, base_name: str) -> str:
        """<base name>.<account number>.<environment API domain>, without a port, e.g. in local development."""
        domain = smarter_settings.environment_api_domain.split(":")[0]
        return f"{base_name}.{llmhost.user_profile.account.account_number}.{domain}"

    @staticmethod
    def compute_of(llmhost: LLMHost, spec: SAMLLMHostSpec) -> LLMHostCompute:
        """
        The LLMHost's compute, which it is saved with when it is applied.

        :raises LLMHostConfigurationError: if it has none, and none fits it, or if it does not fit it.
        """
        try:
            if llmhost.compute is None:
                llmhost.compute = resolve_compute(spec, llmhost.user_profile)
                llmhost.save(update_fields=["compute", "updated_at"])
            return llmhost.compute
        except LLMHostComputeError as e:
            raise LLMHostConfigurationError(f"LLMHost {llmhost.name}: {e}") from e

    def context_for(self, llmhost: LLMHost, spec: Optional[SAMLLMHostSpec] = None) -> RenderContext:
        """The render context of the LLMHost's Kubernetes resources."""
        spec = spec or self.spec_of(llmhost)
        base_name = self.base_name(llmhost)
        hostname = spec.network.hostname or self.default_hostname(llmhost, base_name)
        compute = self.compute_of(llmhost, spec)
        return RenderContext(
            base_name=base_name,
            namespace=self.cluster.namespace,
            spec=spec,
            served_name=llmhost.name,
            account_number=llmhost.user_profile.account.account_number,
            hostname=hostname if spec.network.ingress else None,
            cluster_issuer=smarter_settings.environment_api_domain.split(":")[0],
            hf_token=bool(spec.model.tokenSecret),
            api_key=get_engine(spec.engine.name).supports_api_key(),
            platform_name=smarter_settings.platform_name,
            compute=compute.name,
            compute_taint=compute.taint,
        )

    @staticmethod
    def find_secret(llmhost: LLMHost, name: str) -> Secret:
        """A Smarter Secret that the LLMHost's owner may read: their own, else one shared with them."""
        secret = Secret.objects.filter(user_profile=llmhost.user_profile, name=name).first()
        if secret is None:
            secret = Secret.objects.with_read_permission_for(llmhost.user_profile.user).filter(name=name).first()  # type: ignore[attr-defined]
        if secret is None:
            raise LLMHostConfigurationError(f"Secret {name} of LLMHost {llmhost.name} does not exist.")
        return secret

    def secret_value(self, llmhost: LLMHost, name: str) -> str:
        value = self.find_secret(llmhost, name).get_secret()
        if not value:
            raise LLMHostConfigurationError(f"Secret {name} of LLMHost {llmhost.name} is empty or expired.")
        return value

    def ensure_api_key(self, llmhost: LLMHost, spec: SAMLLMHostSpec) -> tuple[Secret, str]:
        """
        The Smarter Secret with the LLMHost's API key, and its value.

        ``network.apiKeySecret`` if set, else the Secret llmhost_<name>_api_key, which is
        created, with a random key, the first time.
        """
        if spec.network.apiKeySecret:
            secret = self.find_secret(llmhost, spec.network.apiKeySecret)
        else:
            name = API_KEY_SECRET_NAME.format(name=llmhost.name)
            secret = Secret.objects.filter(user_profile=llmhost.user_profile, name=name).first()
            if secret is None:
                secret = Secret(
                    name=name,
                    user_profile=llmhost.user_profile,
                    description=f"The API key of LLMHost {llmhost.name}. Generated by Smarter.",
                    encrypted_value=Secret.encrypt(secrets.token_urlsafe(API_KEY_BYTES)),
                )
                secret.save()
                logger.info("%s.ensure_api_key() created Secret %s", logger_prefix, name)
        value = secret.get_secret()
        if not value:
            raise LLMHostConfigurationError(f"Secret {secret.name} of LLMHost {llmhost.name} is empty or expired.")
        return secret, value

    # --- launch -------------------------------------------------------------------

    def plan(self, llmhost: LLMHost) -> list[dict[str, Any]]:
        """
        Preview the Kubernetes resources that :meth:`launch` would apply.

        Secret values are redacted, and nothing is created.
        """
        ctx = self.context_for(llmhost)
        return render_resources(
            ctx, hf_token=REDACTED if ctx.hf_token else None, api_key=REDACTED if ctx.api_key else None
        )

    def authorize_budgets(self, llmhost: LLMHost) -> None:
        """
        Refuse to launch an LLMHost whose compute, owner, or account a budget has locked.

        Running nodes are not removed: the budget only stops more of them being added.

        :raises LLMHostBudgetExceeded: if a budget's resource lock forbids charges to one of them.
        """
        resources = [llmhost.compute, llmhost.user_profile, llmhost.user_profile.account]
        try:
            charge_authorization([r.record_locator for r in resources if r is not None], self.__class__.__name__)
        except SmarterBudgetExceeded as e:
            llmhost.status = Status.ERROR.value
            llmhost.status_message = e.message
            llmhost.save(update_fields=["status", "status_message", "updated_at"])
            llmhost.record_event(EventType.ERROR.value, f"Launch refused: {e.message}")
            llmhost_launch_failed.send(sender=self.__class__, llmhost=llmhost, error=e.message)
            raise LLMHostBudgetExceeded(e.message) from e

    def launch(self, llmhost: LLMHost) -> LLMHostObservation:
        """
        Launch the LLMHost: apply its Kubernetes resources, then give its compute's node group the nodes that it needs.

        It returns as soon as the cluster accepts the resources, and the cloud the node group's
        new size. A new node takes minutes to start, during which :meth:`observe` reports
        ``provisioning``, and the pods wait for it; downloading and loading the weights takes
        minutes more, during which it reports ``pending``, ``downloading`` and ``deploying``, then
        ``active``. Launching a launched LLMHost applies its changed spec.

        :raises LLMHostConfigurationError: if the spec is invalid, does not fit its compute, or a
            Secret does not exist.
        :raises LLMHostClusterError: if the cluster is unavailable, or rejects the resources.
        :raises LLMHostComputeError: if the compute's node group cannot be scaled. The resources
            are applied, so launching again retries.
        :raises LLMHostBudgetExceeded: if a budget forbids more charges to its compute, its owner,
            or their account. Nothing is applied.
        """
        self.authorize_budgets(llmhost)
        spec = self.spec_of(llmhost)
        if not self.cluster.ready:
            raise LLMHostClusterError("The Kubernetes cluster is not available.")
        ctx = self.context_for(llmhost, spec)
        hf_token = self.secret_value(llmhost, spec.model.tokenSecret) if spec.model.tokenSecret else None
        api_key_secret, api_key = (None, None)
        if ctx.api_key:
            api_key_secret, api_key = self.ensure_api_key(llmhost, spec)
        resources = render_resources(ctx, hf_token=hf_token, api_key=api_key)

        try:
            self.cluster.apply(resources)
        except LLMHostClusterError as e:
            llmhost.status = Status.ERROR.value
            llmhost.status_message = str(e)
            llmhost.save(update_fields=["status", "status_message", "updated_at"])
            llmhost.record_event(EventType.ERROR.value, f"Launch failed: {e}")
            llmhost_launch_failed.send(sender=self.__class__, llmhost=llmhost, error=str(e))
            raise

        if not llmhost.is_deployed or not llmhost.deployed_at:
            llmhost.deployed_at = timezone.now()
        # deployed, so that the compute's reconcile counts its pods.
        llmhost.status = Status.PENDING.value
        llmhost.status_message = "Launched. Waiting for the inference server to start."
        llmhost.replicas = spec.scaling.replicas
        llmhost.endpoint_url = ctx.endpoint
        llmhost.public_url = ctx.public_url or ""
        llmhost.health_check_url = ctx.health_check_url
        llmhost.api_key_secret = api_key_secret
        llmhost.save()
        summary = [f"{r['kind']}/{r['metadata']['name']}" for r in resources]
        llmhost.record_event(EventType.LAUNCHED.value, "Applied " + ", ".join(summary), {"resources": summary})

        compute = llmhost.compute
        try:
            state = self.provisioner.reconcile(compute)  # type: ignore[arg-type]
        except LLMHostComputeError as e:
            llmhost.status = Status.ERROR.value
            llmhost.status_message = f"The node group of compute {compute} cannot be scaled: {e}"
            llmhost.save(update_fields=["status", "status_message", "updated_at"])
            llmhost.record_event(EventType.ERROR.value, llmhost.status_message)
            llmhost_launch_failed.send(sender=self.__class__, llmhost=llmhost, error=str(e))
            raise
        if state.actions:
            llmhost.record_event(EventType.NODES_SCALED.value, "; ".join(state.actions), {"compute": compute.name})  # type: ignore[union-attr]
        if state.provisioning:
            llmhost.status = Status.PROVISIONING.value
            llmhost.status_message = f"Compute {compute}: {state.message}"
            llmhost.save(update_fields=["status", "status_message", "updated_at"])
        llmhost_launched.send(sender=self.__class__, llmhost=llmhost, resources=summary)
        logger.info("%s.launch() launched %s: %s", logger_prefix, llmhost, summary)
        return LLMHostObservation(
            status=llmhost.status,
            message=llmhost.status_message,
            replicas=llmhost.replicas,
            endpoint=llmhost.endpoint_url,
            public_url=llmhost.public_url or None,
            checked_at=timezone.now(),
        )

    # --- observability --------------------------------------------------------------

    def observe(self, llmhost: LLMHost, persist: bool = True, probe: bool = True) -> LLMHostObservation:
        """
        Check the LLMHost's status, from its Deployment and pods, and its health.

        :param persist: Save the status to the LLMHost, and record an event if it changed.
        :param probe: Call the engine's health endpoint, when the LLMHost is active.
        """
        now = timezone.now()
        if not self.cluster.ready:
            return LLMHostObservation(
                status=llmhost.status,
                message="The Kubernetes cluster is not available. The status was not checked.",
                replicas=llmhost.replicas,
                ready_replicas=llmhost.ready_replicas,
                endpoint=llmhost.endpoint_url or None,
                public_url=llmhost.public_url or None,
                checked_at=now,
            )
        base_name = self.base_name(llmhost)
        deployment = self.cluster.get("deployment", base_name)
        pods = self.cluster.list_resources("pods", label_selector(base_name))
        status, message, replicas, ready = interpret(deployment, pods)
        status, message = self.provisioning_status(llmhost, status, message)

        healthy = None
        if probe and status == Status.ACTIVE.value and llmhost.health_check_url:
            healthy = self.prober.check(llmhost.health_check_url)
            if healthy is False:
                status = Status.DEGRADED.value
                message = f"{message} The health check at {llmhost.health_check_url} failed."

        observation = LLMHostObservation(
            status=status,
            message=message,
            replicas=replicas,
            ready_replicas=ready,
            healthy=healthy,
            endpoint=llmhost.endpoint_url or None,
            public_url=llmhost.public_url or None,
            pods=[summarize_pod(pod) for pod in pods],
            checked_at=now,
        )
        if persist:
            self._persist(llmhost, observation)
        return observation

    @staticmethod
    def provisioning_status(llmhost: LLMHost, status: str, message: str) -> tuple[str, str]:
        """``provisioning``, if the LLMHost's pods wait for a node that its compute's node group is adding, as of the compute's last reconcile."""
        compute = llmhost.compute
        if status != Status.PENDING.value or compute is None:
            return status, message
        compute.refresh_from_db(fields=["nodegroup_status", "desired_nodes", "ready_nodes", "status_message"])
        adding = compute.nodegroup_status in (NodeGroupStatus.CREATING, NodeGroupStatus.UPDATING)
        if adding or compute.ready_nodes < compute.desired_nodes:
            return Status.PROVISIONING.value, f"Compute {compute.name}: {compute.status_message}"
        return status, message

    def _persist(self, llmhost: LLMHost, observation: LLMHostObservation) -> None:
        old_status = llmhost.status
        llmhost.status = observation.status
        llmhost.status_message = observation.message
        llmhost.ready_replicas = observation.ready_replicas
        if observation.healthy is not None:
            llmhost.last_health_check_at = observation.checked_at
            llmhost.last_health_ok = observation.healthy
        llmhost.save(
            update_fields=[
                "status",
                "status_message",
                "ready_replicas",
                "last_health_check_at",
                "last_health_ok",
                "updated_at",
            ]
        )
        if old_status != observation.status:
            llmhost.record_event(
                EventType.STATUS_CHANGED.value,
                f"{old_status} -> {observation.status}: {observation.message}",
                {"from": old_status, "to": observation.status},
            )
            llmhost_status_changed.send(
                sender=self.__class__,
                llmhost=llmhost,
                old_status=old_status,
                new_status=observation.status,
                observation=observation,
            )

    def logs(self, llmhost: LLMHost, tail: int = DEFAULT_LOG_LINES) -> str:
        """The most recent log lines of the LLMHost's inference server."""
        if not self.cluster.ready:
            raise LLMHostClusterError("The Kubernetes cluster is not available.")
        tail = max(1, min(int(tail), MAX_LOG_LINES))
        return self.cluster.logs(label_selector(self.base_name(llmhost)), container=CONTAINER_NAME, tail=tail) or ""

    def report(self, llmhosts: Iterable[LLMHost]) -> dict[str, Any]:
        """Summarize LLMHosts' status, GPUs and cost.

        See :func:`~smarter.apps.llmhost.services.observability.build_report`.
        """
        return build_report(llmhosts)

    # --- destruction ----------------------------------------------------------------

    def destroy(self, llmhost: LLMHost, purge: bool = False) -> None:
        """
        Destroy the LLMHost's Kubernetes resources.

        The LLMHost itself, and its Secrets, remain.

        :param purge: Also delete the model volume, and the weights cached on it. It is also
            deleted when ``storage.retain`` is false. A ``storage.existingClaim`` is never deleted.
        :raises LLMHostClusterError: if the cluster is unavailable.
        """
        if not self.cluster.ready:
            raise LLMHostClusterError("The Kubernetes cluster is not available.")
        try:
            spec: Optional[SAMLLMHostSpec] = self.spec_of(llmhost)
        except LLMHostConfigurationError:
            spec = None
        base_name = self.base_name(llmhost)
        kinds = list(MANAGED_KINDS)
        delete_volume = purge or (spec is not None and not spec.storage.retain)
        if delete_volume:
            # an existingClaim is not labeled, so it is never selected.
            kinds.append(VOLUME_KIND)
        self.cluster.delete(kinds, label_selector(base_name))
        if spec is None or spec.network.ingress:
            # cert-manager creates the TLS Secret without the LLMHost's labels.
            self.cluster.delete_named("secret", f"{base_name}-tls")

        details = {
            "purge": delete_volume,
            "uptimeHours": llmhost.uptime_hours,
            "estimatedCost": str(llmhost.estimated_cost) if llmhost.estimated_cost is not None else None,
        }
        llmhost.status = Status.INACTIVE.value
        llmhost.status_message = "Destroyed." + ("" if delete_volume else " The model volume was kept.")
        llmhost.ready_replicas = 0
        llmhost.last_health_ok = None
        llmhost.save()
        llmhost.record_event(EventType.DESTROYED.value, llmhost.status_message, details)
        llmhost_destroyed.send(sender=self.__class__, llmhost=llmhost, purge=delete_volume)
        logger.info("%s.destroy() destroyed %s, purge=%s", logger_prefix, llmhost, delete_volume)
        self.release_compute(llmhost)

    def release_compute(self, llmhost: LLMHost) -> Optional[ComputeState]:
        """
        Remove the nodes of the LLMHost's compute that no LLMHost needs any more, e.g. its own, after it is destroyed.

        A failure is logged, not raised: the compute is reconciled again by the ``reconcile_llmhost_compute`` task.
        """
        if llmhost.compute is None:
            return None
        try:
            state = self.provisioner.reconcile(llmhost.compute)
        except LLMHostComputeError as e:
            logger.error("%s.release_compute() %s: %s", logger_prefix, llmhost.compute, e)
            return None
        if state.actions:
            llmhost.record_event(
                EventType.NODES_SCALED.value, "; ".join(state.actions), {"compute": llmhost.compute.name}
            )
        return state

    def delete(self, llmhost: LLMHost) -> None:
        """
        Delete the LLMHost: destroy its Kubernetes resources, including the model volume, and the.

        API key Secret that Smarter generated for it, then the LLMHost.

        If the cluster is unavailable, the LLMHost is deleted only if it is not deployed.
        """
        if self.cluster.ready:
            self.destroy(llmhost, purge=True)
        elif llmhost.is_deployed:
            raise LLMHostClusterError(
                f"LLMHost {llmhost.name} is deployed, and the Kubernetes cluster is not available to destroy it."
            )
        generated = API_KEY_SECRET_NAME.format(name=llmhost.name)
        Secret.objects.filter(user_profile=llmhost.user_profile, name=generated).delete()
        llmhost.delete()


__all__ = ["LLMHostService"]
