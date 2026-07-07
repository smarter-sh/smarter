# pylint: disable=W0718,C0302
"""Smarter API Orchestrator Manifest handler."""

import datetime
from typing import Optional, Type

from django.db import transaction
from django.forms.models import model_to_dict
from django.http import HttpRequest
from rest_framework.serializers import ModelSerializer
from taggit.managers import TaggableManager

from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llm_client.models import LLMClient  # adjust to actual location
from smarter.apps.orchestrator.enum import HarnessRole, OrchestrationStrategy
from smarter.apps.orchestrator.manifest.models.orchestrator.const import MANIFEST_KIND
from smarter.apps.orchestrator.manifest.models.orchestrator.metadata import (
    SAMOrchestratorMetadata,
)
from smarter.apps.orchestrator.manifest.models.orchestrator.model import SAMOrchestrator
from smarter.apps.orchestrator.manifest.models.orchestrator.spec import (
    SAMOrchestratorHarnessConfig,
    SAMOrchestratorSpec,
    SAMOrchestratorSpecConfig,
)
from smarter.apps.orchestrator.manifest.models.orchestrator.status import (
    SAMOrchestratorStatus,
)
from smarter.apps.orchestrator.models import Orchestrator, OrchestratorHarness
from smarter.apps.plugin.signals import broker_ready
from smarter.common.utils.decorators import camel_case
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import (
    AbstractBroker,
    SAMBrokerError,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
)
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
    SCLIResponseGetData,
)

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.ORCHESTRATOR, SmarterWaffleSwitches.MANIFEST_LOGGING]
)

MAX_RESULTS = 1000


class SAMOrchestratorBrokerError(SAMBrokerError):
    """Base exception for Smarter API Orchestrator Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Orchestrator Manifest Broker Error"


class OrchestratorSerializer(ModelSerializer):
    """Django ORM model serializer for get()."""

    # pylint: disable=C0115
    class Meta:
        model = Orchestrator
        fields = ["__all__"]


class SAMOrchestratorBroker(AbstractBroker):
    """
    Broker for :py:class:`SAM <smarter.lib.manifest.models.AbstractSAMMetadataBase>` Orchestrator manifests.

    This class provides a high-level abstraction for managing orchestrator manifests
    within the Smarter platform. It acts as the central coordinator for the
    lifecycle of orchestrator manifests, bridging the gap between declarative YAML
    files and persistent application state.

    The broker is responsible for:

    - Managing the lifecycle of orchestrator manifests, including loading, validation,
      and parsing of YAML files.
    - Initializing Pydantic models from manifest data to ensure robust schema
      validation and serialization.
    - Integrating with Django ORM models that represent orchestrator manifests,
      supporting creation, update, deletion, and querying of database records.
    - Transforming data between Django ORM models and Pydantic models to enable
      seamless conversion between database and API representations.
    - Reconciling the manifest's declarative harnesses list against
      OrchestratorHarness membership rows, since harness membership is a
      many-to-many relationship through LLMClient rather than a column on
      Orchestrator itself — see sync_harnesses().
    - Ensuring atomic and consistent application of changes using Django's
      transaction management.
    - Providing detailed logging and error handling integrated with the Smarter
      platform's diagnostics systems.

    This broker is a key component in the deployment, configuration, and
    lifecycle management of orchestrators in the Smarter Framework.
    """

    # override the base abstract manifest model with the Orchestrator model
    _manifest: Optional[SAMOrchestrator] = None
    _pydantic_model: Type[SAMOrchestrator] = SAMOrchestrator
    _orchestrator: Optional[Orchestrator] = None
    _name: Optional[str] = None
    _ready: bool = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        msg = f"{self.formatted_class_name}.__init__() broker for {self.kind} {self.name} is {self.ready_state}."
        logger.info(msg)

    @property
    def SerializerClass(self) -> Type[OrchestratorSerializer]:
        """
        The Django ORM model serializer class for the Orchestrator.

        :returns: The Orchestrator Django ORM model serializer class.
        :rtype: Type[ModelSerializer]
        """
        return OrchestratorSerializer

    @property
    def ready(self) -> bool:
        """
        Check if the broker is ready for operations.

        :returns: ``True`` if the broker is ready, ``False`` otherwise.
        :rtype: bool
        """
        if self._ready:
            return self._ready
        retval = super().ready
        if not retval:
            logger.debug("%s.ready() AbstractBroker is not ready for %s", self.formatted_class_name, self.kind)
            return False
        retval = self.manifest is not None or self.account is not None
        logger.debug(
            "%s.ready() manifest presence indicates ready=%s for %s",
            self.formatted_class_name,
            retval,
            self.kind,
        )
        if retval:
            self._ready = True
            broker_ready.send(sender=self.__class__, broker=self)
        return self._ready

    @property
    def orchestrator(self) -> Optional[Orchestrator]:
        """
        Provides access to the Django ORM model instance representing the current Smarter Orchestrator.

        :returns: The Django ORM Orchestrator instance if found or created, otherwise ``None`` if neither
                  a database record nor a manifest is available.
        :rtype: Optional[Orchestrator]

        .. admonition:: FIX NOTE

            This should be refactored/removed in favor of orm_instance. There is no logic
            in this property that merits it overriding the parent orm_instance property.

        .. admonition:: FIX NOTE

            This is breaking an unwritten rule of Smarter resources in that it is
            lazily **creating** a database record on a property getter.
            Creating/updating database records, and syncing harness membership,
            should be handled in apply().
        """
        if self._orchestrator:
            return self._orchestrator

        try:
            self._orchestrator = Orchestrator.get_cached_object(
                invalidate=True, user_profile=self.user_profile, name=self.name
            )  # type: ignore
            logger.debug(
                "%s.orchestrator() retrieved existing Orchestrator instance %s owned by %s from database.",
                self.formatted_class_name,
                self._orchestrator,
                self.user_profile,
            )
            return self._orchestrator
        except Orchestrator.DoesNotExist:
            self._orchestrator = None

        logger.debug(
            "%s.orchestrator() Orchestrator instance not found for user_profile %s. Attempting to create a new instance.",
            self.formatted_class_name,
            self.user_profile,
        )
        if self.manifest:
            data = self.manifest_to_django_orm()
            data["user_profile"] = self.user_profile
            logger.debug("%s.orchestrator() Creating new Orchestrator with data: %s", self.formatted_class_name, data)
            tags = data.pop("tags", [])
            self._orchestrator = Orchestrator.objects.create(**data)
            if self._orchestrator and tags:
                self._orchestrator.tags.set(tags)
            self._created = True
            logger.warning(
                "%s.orchestrator() lazily created new Orchestrator instance %s owned by %s. This logic should be handled in apply().",
                self.formatted_class_name,
                self._orchestrator,
                self.user_profile,
            )
        else:
            logger.warning(
                "%s.orchestrator() %s not found for user_profile %s",
                self.formatted_class_name,
                self._orchestrator,
                self.user_profile,
            )

        return self._orchestrator

    def manifest_to_django_orm(self) -> dict:
        """
        Convert the Smarter API Orchestrator manifest into a dictionary suitable for creating or updating a Django ORM Orchestrator model.

        The manifest's ``harnesses`` list is intentionally excluded — it isn't a
        column on Orchestrator, it's a many-to-many relationship through
        OrchestratorHarness. Harness membership is reconciled separately via
        sync_harnesses(), which must be called after the Orchestrator instance
        has been saved (an unsaved Orchestrator has no pk to attach memberships to).

        :returns: A dictionary containing all fields required to create or update a Django ORM Orchestrator model.
        :rtype: dict

        :raises SAMBrokerErrorNotReady: If the manifest is not loaded or cannot be found.
        :raises SAMOrchestratorBrokerError: If the manifest configuration cannot be converted to a dictionary.
        """
        if not self.manifest:
            raise SAMBrokerErrorNotReady(
                f"Manifest not loaded for {self.kind} broker. Cannot convert to Django ORM.", thing=self.kind
            )
        metadata = super().manifest_to_django_orm()

        config_dump = self.manifest.spec.config.model_dump(mode="json")
        config_dump.pop("harnesses", None)
        config_dump = self.to_snake_case(config_dump)
        if not isinstance(config_dump, dict):
            raise SAMOrchestratorBrokerError(
                f"Failed to convert {self.kind} {self.manifest.metadata.name} to dict. Got {type(config_dump)}",
                thing=self.kind,
            )
        retval = {
            **metadata,
            **config_dump,
        }
        logger.debug(
            "%s.manifest_to_django_orm() converted manifest to Django ORM dict: %s",
            self.formatted_class_name,
            retval,
        )

        return retval

    def sync_harnesses(self) -> None:
        """
        Reconcile OrchestratorHarness membership rows against the manifest's.

        ``harnesses`` list. The manifest is treated as the full desired state:
        memberships not present in the manifest are deleted, memberships present
        are created or updated, matched on (orchestrator, llm_client) per the
        model's unique_together constraint.

        Must be called from within apply()'s transaction, after self.orchestrator
        has been saved.

        :raises SAMBrokerErrorNotReady: If the manifest is not loaded.
        :raises SAMOrchestratorBrokerError: If the Orchestrator isn't saved yet, or
            a referenced LLMClient can't be resolved for this account.
        """
        if not self.manifest or not self.manifest.spec:
            raise SAMBrokerErrorNotReady(
                f"Manifest not loaded for {self.kind} broker. Cannot sync harnesses.", thing=self.kind
            )
        if not isinstance(self.orchestrator, Orchestrator) or not self.orchestrator.pk:
            raise SAMOrchestratorBrokerError(
                f"Orchestrator {self.name} is not saved. Cannot sync harnesses.", thing=self.kind
            )

        harness_configs: list[SAMOrchestratorHarnessConfig] = self.manifest.spec.config.harnesses
        seen_llm_client_ids = set()

        for harness_config in harness_configs:
            try:
                llm_client = LLMClient.objects.get(
                    user_profile__account=self.account, name=harness_config.llmClientName
                )
            except LLMClient.DoesNotExist as e:
                raise SAMOrchestratorBrokerError(
                    f"LLMClient '{harness_config.llmClientName}' not found for account {self.account}",
                    thing=self.kind,
                ) from e

            OrchestratorHarness.objects.update_or_create(
                orchestrator=self.orchestrator,
                llm_client=llm_client,
                defaults={
                    "role": harness_config.role.value,
                    "execution_order": harness_config.executionOrder,
                    "is_active": harness_config.isActive,
                    "config": harness_config.config,
                },
            )
            seen_llm_client_ids.add(llm_client.id)

        stale = self.orchestrator.harnesses.exclude(llm_client_id__in=seen_llm_client_ids)
        stale_count = stale.count()
        if stale_count:
            logger.debug(
                "%s.sync_harnesses() removing %s stale harness(es) for %s not present in manifest",
                self.formatted_class_name,
                stale_count,
                self.orchestrator.name,
            )
            stale.delete()

    @camel_case()
    def django_orm_to_manifest_dict(self) -> Optional[dict]:
        """
        Transform the Django ORM Orchestrator model instance into a dictionary compatible with the Smarter API Orchestrator manifest format.

        :returns: A dictionary representing the Smarter API Orchestrator manifest, or ``None`` if the Orchestrator model is not set.
        :rtype: Optional[dict]

        :raises SAMOrchestratorBrokerError: If the ORM model cannot be converted to a manifest dictionary.
        """
        if not self.account:
            raise SAMBrokerErrorNotReady(
                f"Account not loaded for {self.kind} broker. Cannot convert Django ORM to manifest dict.",
                thing=self.kind,
            )
        if not self.user_profile:
            raise SAMBrokerErrorNotReady(
                f"User profile not loaded for {self.kind} broker. Cannot convert Django ORM to manifest dict.",
                thing=self.kind,
            )
        if not self.orchestrator:
            logger.warning(
                "%s.django_orm_to_manifest_dict() called without an Orchestrator. This could affect broker operations.",
                self.formatted_class_name,
            )
            return None
        orchestrator_dict = model_to_dict(self.orchestrator)
        orchestrator_dict = self.to_camel_case(orchestrator_dict)
        if not isinstance(orchestrator_dict, dict):
            raise SAMOrchestratorBrokerError(
                f"Failed to convert {self.kind} {self.orchestrator.name} to dict", thing=self.kind
            )
        orchestrator_dict.pop("id", None)
        orchestrator_dict.pop("name", None)
        orchestrator_dict.pop("description", None)
        orchestrator_dict.pop("version", None)
        # raw m2m pk list from model_to_dict() — the "harnesses" block built
        # below is the manifest-shaped equivalent, with role/order/config attached.
        orchestrator_dict.pop("llmClients", None)
        # fields owned by status, not spec — model_to_dict() pulls these in
        # via to_camel_case() but SAMOrchestratorSpec doesn't accept them.
        for status_field in ("userProfile", "createdAt", "updatedAt", "recordLocator"):
            orchestrator_dict.pop(status_field, None)

        harnesses = [
            SAMOrchestratorHarnessConfig(
                llmClientName=membership.llm_client.name,
                role=HarnessRole(membership.role),
                executionOrder=membership.execution_order,
                isActive=membership.is_active,
                config=membership.config,
            )
            for membership in self.orchestrator.harnesses.select_related("llm_client").order_by("execution_order")
        ]
        orchestrator_dict["harnesses"] = [harness.model_dump(mode="json") for harness in harnesses]

        meta = SAMOrchestratorMetadata(
            name=self.orchestrator.name,
            description=self.orchestrator.description,
            version=self.orchestrator.version,
            tags=self.orchestrator.tags_list,
            annotations=self.orchestrator.annotations if isinstance(self.orchestrator.annotations, list) else [],
        )
        spec_config = SAMOrchestratorSpecConfig(**orchestrator_dict)
        spec = SAMOrchestratorSpec(config=spec_config)
        status = SAMOrchestratorStatus(
            accountNumber=self.account.account_number,
            username=self.user_profile.user.username,
            recordLocator=self.orchestrator.record_locator,
            created=self.orchestrator.created_at,
            modified=self.orchestrator.updated_at,
        )
        model = SAMOrchestrator(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=meta,
            spec=spec,
            status=status,
        )

        logger.debug(
            "%s.django_orm_to_manifest_dict() converted Orchestrator %s to manifest dict: %s",
            self.formatted_class_name,
            self.orchestrator.name,
            model.model_dump(),
        )
        return model.model_dump()

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def formatted_class_name(self) -> str:
        """
        Returns a formatted string representing the class name for logging purposes.

        :returns: A string containing the formatted class name, suitable for use in log output.
        :rtype: str
        """
        class_name = f"{SAMOrchestratorBroker.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    @property
    def kind(self) -> str:
        """
        Returns the manifest kind for the Smarter API Orchestrator.

        :returns: The manifest kind string for the Smarter API Orchestrator.
        :rtype: str
        """
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMOrchestrator]:
        """
        Returns the Smarter API Orchestrator manifest as a Pydantic model.

        :returns: An instance of ``SAMOrchestrator`` representing the orchestrator manifest, or ``None``
                if the manifest cannot be initialized.
        :rtype: Optional[SAMOrchestrator]
        """
        if self._manifest:
            if not isinstance(self._manifest, SAMOrchestrator):
                raise SAMOrchestratorBrokerError("Cached manifest is not a SAMOrchestrator instance", thing=self.kind)
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            logger.debug(
                "%s.manifest() initializing %s from SAMLoader with name %s",
                self.formatted_class_name,
                self.kind,
                self.loader.manifest_metadata.get(SAMMetadataKeys.NAME.value, "unknown"),
            )
            self._manifest = SAMOrchestrator(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMOrchestratorMetadata(**self.loader.manifest_metadata),
                spec=SAMOrchestratorSpec(**self.loader.manifest_spec),
            )
            return self._manifest
        if self._orchestrator:
            self._manifest = self.django_orm_to_manifest_dict()  # type: ignore
            if self._manifest:
                logger.debug(
                    "%s.manifest() initialized from loader for existing Orchestrator %s with name %s",
                    self.formatted_class_name,
                    self._orchestrator,
                    self._orchestrator.name,
                )
                return self._manifest
        else:
            logger.warning(
                "%s.manifest() could not initialize",
                self.formatted_class_name,
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def cache_invalidations(self) -> None:
        """
        Handle broker specific cache invalidation logic.

        .. returns: None
        .. rtype: None
        """
        logger.debug("%s.cache_invalidations() called.", self.formatted_class_name)

        # 1.) invalidate the Orchestrator cache itself.
        Orchestrator.get_cached_object(pk=self.orchestrator.id, invalidate=True)  # type: ignore

        # 2.) invalidate list-level caches for this user_profile.
        Orchestrator.get_cached_objects(user_profile=self.user_profile, invalidate=True)

        return super().cache_invalidations()

    @property
    def ORMMetaModelClass(self) -> Type[Orchestrator]:
        """
        Return the Django ORM meta model class for the broker.

        :return: The Django ORM meta model class definition for the broker.
        :rtype: Type[Orchestrator]
        """
        return Orchestrator

    @property
    def ORMModelClass(self) -> Type[Orchestrator]:
        """
        The Django ORM model class for the Orchestrator.

        :returns: The Orchestrator Django ORM model class.
        :rtype: Type[Orchestrator]
        """
        return Orchestrator

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return an example manifest for the Smarter API Orchestrator.

        :returns: A JSON response containing an example Smarter API Orchestrator manifest.
        :rtype: SmarterJournaledJsonResponse
        """

        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)

        meta_data = SAMOrchestratorMetadata(
            name="example_orchestrator",
            description="This is an example orchestrator manifest generated by the SAMOrchestratorBroker. It serves as a template for creating your own orchestrator manifests.",
            version="1.0.0",
            tags=["example", "template", "agentic"],
            annotations=[
                {"pattern": "supervisor-worker"},
            ],
        )

        config = SAMOrchestratorSpecConfig(
            strategy=OrchestrationStrategy.SUPERVISOR,
            maxIterations=10,
            isActive=True,
            harnesses=[
                SAMOrchestratorHarnessConfig(
                    llmClientName="example-planner-client",
                    role=HarnessRole.PLANNER,
                    executionOrder=0,
                    isActive=True,
                    config={"temperature": 0.2},
                ),
                SAMOrchestratorHarnessConfig(
                    llmClientName="example-executor-client",
                    role=HarnessRole.EXECUTOR,
                    executionOrder=1,
                    isActive=True,
                    config={"temperature": 0.7},
                ),
            ],
        )

        spec = SAMOrchestratorSpec(config=config)
        status = SAMOrchestratorStatus(
            accountNumber=smarter_cached_objects.smarter_account.account_number,
            username=smarter_cached_objects.smarter_admin.username,
            recordLocator="abc123def456",
            created=datetime.datetime.now(),
            modified=datetime.datetime.now(),
        )
        model = SAMOrchestrator(
            apiVersion=self.api_version, kind=self.kind, metadata=meta_data, spec=spec, status=status
        )

        return self.json_response_ok(command=command, data=model.model_dump())

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        data = []
        name = kwargs.get(SAMMetadataKeys.NAME.value, None)
        name = self.clean_cli_param(param=name, param_name="name", url=self.smarter_build_absolute_uri(request))

        if self.user_profile is None:
            raise SAMBrokerErrorNotReady("user_profile is not set.")

        if name:
            orchestrators = Orchestrator.objects.filter(user_profile__account=self.account, name=name)
        else:
            orchestrators = Orchestrator.objects.filter(user_profile__account=self.account)
        orchestrators = orchestrators.with_ownership_permission_for(self.user_profile.user).order_by("name")[
            :MAX_RESULTS
        ]
        logger.debug(
            "%s.get() found %s Orchestrators for account %s",
            self.formatted_class_name,
            orchestrators.count(),
            self.account,
        )

        for orchestrator in orchestrators:
            try:
                model_dump = OrchestratorSerializer(orchestrator).data
                if not model_dump:
                    raise SAMOrchestratorBrokerError(
                        f"Model dump failed for {self.kind} {orchestrator.name}", thing=self.kind, command=command
                    )
                camel_cased_model_dump = self.to_camel_case(model_dump)
                data.append(camel_cased_model_dump)
            except Exception as e:
                logger.error(
                    "%s.get() failed to serialize %s %s",
                    self.formatted_class_name,
                    self.kind,
                    orchestrator.name,
                    exc_info=True,
                )
                raise SAMOrchestratorBrokerError(
                    f"Failed to serialize {self.kind} {orchestrator.name}", thing=self.kind, command=command
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: name,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=OrchestratorSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    # pylint: disable=too-many-branches
    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Apply the manifest.

        Copy the manifest data to the Django ORM model and save it, then
        reconcile OrchestratorHarness membership against the manifest's
        harnesses list via sync_harnesses(). Fields that are readonly at
        the ORM level are stripped from the update dict before the save()
        call, since they're either DB-managed (id, timestamps) or handled
        through a different API (tags).
        """
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)
        if not self.ready:
            raise SAMBrokerErrorNotReady(
                f"{self.kind} {self.name} broker is not ready", thing=self.kind, command=command
            )
        if not self.manifest:
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        if not self.manifest.spec:
            raise SAMBrokerErrorNotReady(
                f"{self.kind} {self.name} manifest spec not found", thing=self.kind, command=command
            )
        if not isinstance(self.orchestrator, Orchestrator):
            raise SAMOrchestratorBrokerError(f"Orchestrator {self.name} not found", thing=self.kind, command=command)
        with transaction.atomic():
            readonly_fields = ["id", "created_at", "updated_at", "tags"]
            try:
                data = self.manifest_to_django_orm()
                tags = data.get("tags", [])
                for field in readonly_fields:
                    data.pop(field, None)
                for key, value in data.items():
                    setattr(self.orchestrator, key, value)
                if self.orchestrator.user_profile != self.user_profile:
                    raise SAMOrchestratorBrokerError(
                        f"User profile mismatch for {self.kind} {self.manifest.metadata.name}",
                        thing=self.kind,
                        command=command,
                    )
                self.orchestrator.save()
                self.sync_harnesses()

                # Fix note: occasionally seeing AttributeError: 'list' object has no attribute 'set'
                # in the logs, which is why this is wrapped in a try/except block.
                try:
                    if not isinstance(self.orchestrator.tags, TaggableManager):
                        logger.warning(
                            "%s.apply() orchestrator.tags is a list instead of a TaggableManager for %s %s owned by %s. This is unexpected and may indicate an issue with the Orchestrator model definition or the database state. Tags=%s",
                            self.formatted_class_name,
                            self.kind,
                            self.manifest.metadata.name,
                            self.user_profile,
                            tags,
                        )
                    else:
                        self.orchestrator.tags.set(tags)
                # pylint: disable=broad-except
                except Exception as e:
                    logger.error(
                        "%s.apply() failed to set tags for %s %s owned by %s. Tags=%s. Error: %s",
                        self.formatted_class_name,
                        self.kind,
                        self.manifest.metadata.name,
                        self.user_profile,
                        tags,
                        e,
                        exc_info=True,
                    )
                self.orchestrator.refresh_from_db()
            except Exception as e:
                logger.error(
                    "%s.apply() failed to save %s %s owned by %s. Error: %s",
                    self.formatted_class_name,
                    self.kind,
                    self.manifest.metadata.name,
                    self.user_profile,
                    e,
                    exc_info=True,
                )
                raise SAMOrchestratorBrokerError(
                    f"Failed to apply {self.kind} {self.manifest.metadata.name}", thing=self.kind, command=command
                ) from e

            self.cache_invalidations()
            return self.json_response_ok(command=command, data=self.to_json())

    def prompt(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.prompt.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Prompt not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        if self.name is None:
            raise SAMBrokerErrorNotReady(f"{self.kind} name property is not set.", thing=self.kind, command=command)
        if self.orchestrator:
            try:
                data = self.django_orm_to_manifest_dict()
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                logger.error(
                    "%s.describe() failed to describe %s %s",
                    self.formatted_class_name,
                    self.kind,
                    self.name,
                    exc_info=True,
                )
                raise SAMOrchestratorBrokerError(
                    f"Failed to describe {self.kind} {self.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        if self.name is None:
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        if self.orchestrator:
            try:
                self.orchestrator.delete()
                self.cache_invalidations()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                logger.error(
                    "%s.delete() failed to delete %s %s",
                    self.formatted_class_name,
                    self.kind,
                    self.name,
                    exc_info=True,
                )
                raise SAMOrchestratorBrokerError(
                    f"Failed to delete {self.kind} {self.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerError(f"{self.kind} {self.name} deploy() is not implemented.", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerError(
            f"{self.kind} {self.name} undeploy() is not implemented.", thing=self.kind, command=command
        )

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        data = {}
        return self.json_response_ok(command=command, data=data)
