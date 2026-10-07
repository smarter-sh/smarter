# pylint: disable=W0718,C0302,R0904
"""
Smarter API Guardrail Manifest handler.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import datetime
from typing import Any, List, Optional, Type

from django.db import transaction
from django.db.models import Count, Max, Q
from django.http import HttpRequest
from django.utils import timezone
from rest_framework.serializers import ModelSerializer

from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.guardrail.caching import (
    invalidate_all_cached_guardrails_for_user_profile,
)
from smarter.apps.guardrail.manifest.enum import (
    SAMGuardrailAction,
    SAMGuardrailCategory,
    SAMGuardrailDetector,
    SAMGuardrailStage,
    SAMGuardrailStrategy,
)
from smarter.apps.guardrail.manifest.models.guardrail.const import MANIFEST_KIND
from smarter.apps.guardrail.manifest.models.guardrail.metadata import (
    SAMGuardrailMetadata,
)
from smarter.apps.guardrail.manifest.models.guardrail.model import SAMGuardrail
from smarter.apps.guardrail.manifest.models.guardrail.spec import (
    SAMGuardrailSpec,
    SAMGuardrailSpecConfig,
)
from smarter.apps.guardrail.manifest.models.guardrail.status import SAMGuardrailStatus
from smarter.apps.guardrail.models import (
    Guardrail,
    GuardrailDisposition,
    GuardrailEvent,
)
from smarter.apps.guardrail.serializers import GuardrailSerializer
from smarter.apps.plugin.signals import broker_ready
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import (
    AbstractBroker,
    SAMBrokerError,
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
    memoized_dependencies,
)
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
    SCLIResponseGetData,
)

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.GUARDRAIL_LOGGING, SmarterWaffleSwitches.MANIFEST_LOGGING]
)

MAX_RESULTS = 1000
STATUS_DAYS = 30
"""The number of days of events that the status reports."""

CONFIG_FIELDS = {
    # manifest spec.config field: Django ORM Guardrail field
    "stage": "stage",
    "category": "category",
    "strategy": "strategy",
    "pattern": "pattern",
    "threshold": "threshold",
    "action": "action",
    "replacement": "replacement",
    "message": "message",
    "severity": "severity",
    "mode": "mode",
    "failClosed": "fail_closed",
    "priority": "priority",
    "isActive": "is_active",
}
"""The spec.config fields that are Guardrail fields."""

STRATEGY_FIELDS = {
    SAMGuardrailStrategy.REGEX.value: ["flags"],
    SAMGuardrailStrategy.KEYWORD.value: ["keywords", "caseSensitive", "wholeWord"],
    SAMGuardrailStrategy.DETECTOR.value: ["detectors"],
    SAMGuardrailStrategy.SEMANTIC.value: ["referenceTexts", "model", "provider"],
    SAMGuardrailStrategy.MODERATION.value: ["categories", "model", "provider"],
    SAMGuardrailStrategy.LLM_JUDGE.value: ["judgePrompt", "model", "provider"],
}
"""The spec.config fields of each strategy, which are stored in the Guardrail's config."""


class SAMGuardrailBrokerError(SAMBrokerError):
    """Base exception for Smarter API Guardrail Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Guardrail Manifest Broker Error"


class SAMGuardrailBroker(AbstractBroker):
    """
    Broker for :py:class:`SAM <smarter.lib.manifest.models.AbstractSAMMetadataBase>` Guardrail manifests.

    The broker converts between Guardrail manifests and the
    :class:`~smarter.apps.guardrail.models.Guardrail` Django ORM model, and implements the
    ``smarter`` CLI commands for Guardrails: ``apply``, ``describe``, ``get``, ``delete`` and
    ``example_manifest``. Guardrails are not deployed, so ``deploy`` and ``undeploy`` are not
    implemented. LLMClients use Guardrails by listing them in their ``spec.guardrails``.
    """

    _manifest: Optional[SAMGuardrail] = None
    _pydantic_model: Type[SAMGuardrail] = SAMGuardrail
    _guardrail: Optional[Guardrail] = None
    _name: Optional[str] = None
    _ready: bool = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        logger.info(
            "%s.__init__() broker for %s %s is %s.", self.formatted_class_name, self.kind, self.name, self.ready_state
        )

    @property
    def SerializerClass(self) -> Type[ModelSerializer]:
        """The Django ORM model serializer class for the Guardrail."""
        return GuardrailSerializer

    @property
    def ready(self) -> bool:
        """A broker is ready if it has a manifest, or an account."""
        if self._ready:
            return self._ready
        if not super().ready:
            return False
        if self.manifest is not None or self.account is not None:
            self._ready = True
            broker_ready.send(sender=self.__class__, broker=self)
        return self._ready

    @property
    def guardrail(self) -> Optional[Guardrail]:
        """The user's Guardrail with the broker's name, if it exists.

        It is never created here: :meth:`apply` does that.
        """
        if self._guardrail:
            return self._guardrail
        if not self.user_profile or not self.name:
            return None
        self._guardrail = Guardrail.objects.filter(user_profile=self.user_profile, name=self.name).first()
        return self._guardrail

    def manifest_to_django_orm(self) -> dict[str, Any]:
        """
        Convert the manifest into a dict of Django ORM Guardrail fields.

        The strategy's fields, e.g. ``keywords`` or ``judgePrompt``, are stored in ``config``,
        with their manifest names. The other strategies' fields are not stored.

        :raises SAMBrokerErrorNotReady: If the manifest is not loaded.
        """
        if not self.manifest:
            raise SAMBrokerErrorNotReady(f"Manifest not loaded for {self.kind} broker.", thing=self.kind)
        config = self.manifest.spec.config
        retval = {**super().manifest_to_django_orm()}
        for manifest_field, orm_field in CONFIG_FIELDS.items():
            retval[orm_field] = getattr(config, manifest_field)
        retval["config"] = {field: getattr(config, field) for field in STRATEGY_FIELDS.get(config.strategy, [])}
        return retval

    def status_for(self, guardrail: Guardrail) -> dict[str, Any]:
        """Return a Guardrail's events of the last 30 days.

        The LLMClients that use it are reported in ``status.dependencies``.
        """
        since = timezone.now() - datetime.timedelta(days=STATUS_DAYS)
        counts = GuardrailEvent.objects.filter(guardrail=guardrail, created_at__gte=since).aggregate(
            triggered=Count("id", filter=~Q(disposition=GuardrailDisposition.ERROR)),
            blocked=Count("id", filter=Q(disposition=GuardrailDisposition.BLOCKED)),
            errors=Count("id", filter=Q(disposition=GuardrailDisposition.ERROR)),
            last=Max("created_at", filter=~Q(disposition=GuardrailDisposition.ERROR)),
        )
        return {
            "triggered": counts["triggered"],
            "blocked": counts["blocked"],
            "errors": counts["errors"],
            "lastTriggered": counts["last"],
        }

    def django_orm_to_manifest_dict(self) -> Optional[dict]:
        """Convert the Guardrail into a manifest dict, with its status."""
        if not self.account or not self.user_profile:
            raise SAMBrokerErrorNotReady(
                f"Account and user profile are required to describe a {self.kind}.", thing=self.kind
            )
        guardrail = self.guardrail
        if not guardrail:
            return None
        config_data = {
            manifest_field: getattr(guardrail, orm_field) for manifest_field, orm_field in CONFIG_FIELDS.items()
        }
        config_data.update(guardrail.settings)
        meta = SAMGuardrailMetadata(
            name=guardrail.name,
            description=guardrail.description,
            version=guardrail.version,
            tags=guardrail.tags_list,
            annotations=guardrail.annotations if isinstance(guardrail.annotations, list) else [],
        )
        spec = SAMGuardrailSpec(config=SAMGuardrailSpecConfig(**config_data))
        status = SAMGuardrailStatus(
            accountNumber=self.account.account_number,
            username=self.user_profile.user.username,
            recordLocator=guardrail.record_locator,
            created=guardrail.created_at,
            modified=guardrail.updated_at,
            **self.status_for(guardrail),
        )
        model = SAMGuardrail(apiVersion=self.api_version, kind=self.kind, metadata=meta, spec=spec, status=status)
        return model.model_dump()

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def formatted_class_name(self) -> str:
        """The class name, for logging."""
        return self.formatted_text(f"{SAMGuardrailBroker.__name__}[{id(self)}]")

    @property
    def kind(self) -> str:
        """The manifest kind: Guardrail."""
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMGuardrail]:
        """The Guardrail manifest, as a Pydantic model, from the manifest loader."""
        if self._manifest:
            if not isinstance(self._manifest, SAMGuardrail):
                raise SAMGuardrailBrokerError("Cached manifest is not a SAMGuardrail instance", thing=self.kind)
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMGuardrail(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMGuardrailMetadata(**self.loader.manifest_metadata),
                spec=SAMGuardrailSpec(**self.loader.manifest_spec),
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def cache_invalidations(self) -> None:
        """Invalidate the cached Guardrail, and the user's cached Guardrail lists."""
        if self.guardrail:
            Guardrail.get_cached_object(pk=self.guardrail.pk, invalidate=True)
        if self.user_profile:
            Guardrail.get_cached_objects(user_profile=self.user_profile, invalidate=True)
            invalidate_all_cached_guardrails_for_user_profile(self.user_profile)
        return super().cache_invalidations()

    @property
    def ORMMetaModelClass(self) -> Type[Guardrail]:
        return Guardrail

    @property
    def ORMModelClass(self) -> Type[Guardrail]:
        return Guardrail

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return an example Guardrail manifest: redact personal data from the user's message."""
        command = SmarterJournalCliCommands(self.example_manifest.__name__)
        meta_data = SAMGuardrailMetadata(
            name="example_guardrail",
            description="Redacts credit card numbers and social security numbers from the user's message.",
            version="1.0.0",
            tags=["example", "pii"],
            annotations=[{"smarter.sh/guardrail/purpose": "example"}],
        )
        config = SAMGuardrailSpecConfig(
            stage=SAMGuardrailStage.INPUT.value,
            category=SAMGuardrailCategory.PII.value,
            strategy=SAMGuardrailStrategy.DETECTOR.value,
            detectors=[SAMGuardrailDetector.CREDIT_CARD.value, SAMGuardrailDetector.US_SSN.value],
            action=SAMGuardrailAction.REDACT.value,
            replacement="[REDACTED {label}]",
            severity=4,
            priority=10,
        )
        status = SAMGuardrailStatus(
            accountNumber=smarter_cached_objects.smarter_account.account_number,
            username=smarter_cached_objects.smarter_admin.username,
            recordLocator="abc123def456",
            created=datetime.datetime.now(),
            modified=datetime.datetime.now(),
        )
        model = SAMGuardrail(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=meta_data,
            spec=SAMGuardrailSpec(config=config),
            status=status,
        )
        return self.json_response_ok(command=command, data=model.model_dump())

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return the Guardrails that the user may read, optionally filtered by name."""
        command = SmarterJournalCliCommands(self.get.__name__)
        name = self.clean_cli_param(
            param=kwargs.get(SAMMetadataKeys.NAME.value, None),
            param_name="name",
            url=self.smarter_build_absolute_uri(request),
        )
        if self.user_profile is None:
            raise SAMBrokerErrorNotReady("user_profile is not set.")
        guardrails = Guardrail.objects.with_read_permission_for(self.user_profile.user)  # type: ignore[attr-defined]
        if name:
            guardrails = guardrails.filter(name=name)
        data = [
            self.to_camel_case(GuardrailSerializer(guardrail).data)
            for guardrail in guardrails.order_by("priority", "name")[:MAX_RESULTS]
        ]
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: name,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=GuardrailSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Create or update the Guardrail from the manifest.

        .. note::

            tags are handled separately because they are of type TaggableManager and
            require a different method to set them.
        """
        command = SmarterJournalCliCommands(self.apply.__name__)
        if not self.ready or not self.manifest:
            raise SAMBrokerErrorNotReady(
                f"{self.kind} {self.name} broker is not ready", thing=self.kind, command=command
            )
        data = self.manifest_to_django_orm()
        tags = data.pop("tags", None) or []
        for field in ("id", "created_at", "updated_at"):
            data.pop(field, None)
        with transaction.atomic():
            guardrail = self.guardrail
            if guardrail is None:
                guardrail = Guardrail(**data)
            else:
                for key, value in data.items():
                    setattr(guardrail, key, value)
            try:
                guardrail.save()
                guardrail.tags.set(tags)
            except Exception as e:
                raise SAMGuardrailBrokerError(
                    f"Failed to apply {self.kind} {self.manifest.metadata.name}: {e}", thing=self.kind, command=command
                ) from e
        self._guardrail = guardrail
        self.cache_invalidations()
        return self.json_response_ok(command=command, data=self.to_json())

    def prompt(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = SmarterJournalCliCommands(self.prompt.__name__)
        raise SAMBrokerErrorNotImplemented(message="Prompt not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return the Guardrail as a manifest, with its status."""
        command = SmarterJournalCliCommands(self.describe.__name__)
        if self.name is None:
            raise SAMBrokerErrorNotReady(f"{self.kind} name property is not set.", thing=self.kind, command=command)
        if not self.guardrail:
            raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        try:
            data = self.django_orm_to_manifest_dict()
        except Exception as e:
            raise SAMGuardrailBrokerError(
                f"Failed to describe {self.kind} {self.name}: {e}", thing=self.kind, command=command
            ) from e
        return self.json_response_ok(command=command, data=data)

    @memoized_dependencies
    def dependencies(self) -> List[AbstractBroker]:
        """Return brokers for the LLMClients that use this Guardrail.

        :return: A broker for each LLMClient that lists this Guardrail in its ``spec.guardrails``.
        :rtype: List[AbstractBroker]
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.api.v1.manifests.enum import SAMKinds
        from smarter.apps.llmclient.models import LLMClient, LLMClientGuardrails

        guardrail = self.guardrail
        if not guardrail:
            return []
        llmclients = LLMClient.objects.filter(
            id__in=LLMClientGuardrails.objects.filter(guardrail=guardrail).values("llmclient_id")
        )
        return self.dependency_brokers(SAMKinds.LLM_CLIENT.value, llmclients)

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Delete the Guardrail.

        Refused while LLMClients use it.
        """
        command = SmarterJournalCliCommands(self.delete.__name__)
        if self.name is None or not self.guardrail:
            raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        self.verify_no_dependencies(command)
        try:
            self.cache_invalidations()
            self.guardrail.delete()
            self._guardrail = None
        except Exception as e:
            raise SAMGuardrailBrokerError(
                f"Failed to delete {self.kind} {self.name}", thing=self.kind, command=command
            ) from e
        return self.json_response_ok(command=command, data={})

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = SmarterJournalCliCommands(self.deploy.__name__)
        raise SAMBrokerErrorNotImplemented(
            message=f"{self.kind} {self.name} deploy() is not implemented.", thing=self.kind, command=command
        )

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = SmarterJournalCliCommands(self.undeploy.__name__)
        raise SAMBrokerErrorNotImplemented(
            message=f"{self.kind} {self.name} undeploy() is not implemented.", thing=self.kind, command=command
        )

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = SmarterJournalCliCommands(self.logs.__name__)
        return self.json_response_ok(command=command, data={})
