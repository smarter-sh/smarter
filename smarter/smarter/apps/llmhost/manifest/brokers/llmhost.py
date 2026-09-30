# pylint: disable=W0718,C0302
"""Smarter API LLMHost Manifest handler."""

import datetime
from decimal import Decimal
from typing import Optional, Type

from django.db import transaction
from django.forms.models import model_to_dict
from django.http import HttpRequest
from pydantic import HttpUrl, TypeAdapter
from rest_framework.serializers import ModelSerializer
from taggit.managers import TaggableManager

from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llmhost.enum import (
    ApiFormat,
    CloudProvider,
    DeploymentType,
    InferenceEngine,
    Quantization,
)
from smarter.apps.llmhost.manifest.models.llmhost.const import MANIFEST_KIND
from smarter.apps.llmhost.manifest.models.llmhost.metadata import (
    SAMLLMHostMetadata,
)
from smarter.apps.llmhost.manifest.models.llmhost.model import SAMLLMHost
from smarter.apps.llmhost.manifest.models.llmhost.spec import (
    SAMLLMHostCharacteristicsConfig,
    SAMLLMHostHealthCheckConfig,
    SAMLLMHostInfrastructureConfig,
    SAMLLMHostProvenanceConfig,
    SAMLLMHostServingConfig,
    SAMLLMHostSpec,
    SAMLLMHostSpecConfig,
)
from smarter.apps.llmhost.manifest.models.llmhost.status import SAMLLMHostStatus
from smarter.apps.llmhost.models import (
    LLMHost,
)
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
    __name__, any_switches=[SmarterWaffleSwitches.LLM_HOST_LOGGING, SmarterWaffleSwitches.MANIFEST_LOGGING]
)

MAX_RESULTS = 1000


class SAMLLMHostBrokerError(SAMBrokerError):
    """Base exception for Smarter API LLMHost Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API LLMHost Manifest Broker Error"


class LLMHostSerializer(ModelSerializer):
    """Django ORM model serializer for get()."""

    # pylint: disable=C0115
    class Meta:
        model = LLMHost
        fields = ["__all__"]


class SAMLLMHostBroker(AbstractBroker):
    """
    Broker for :py:class:`SAM <smarter.lib.manifest.models.AbstractSAMMetadataBase>` LLMHost manifests.

    This class provides a high-level abstraction for managing llmhost manifests
    within the Smarter platform. It acts as the central coordinator for the
    lifecycle of llmhost manifests, bridging the gap between declarative YAML
    files and persistent application state.

    The broker is responsible for:

    - Managing the lifecycle of llmhost manifests, including loading, validation,
      and parsing of YAML files.
    - Initializing Pydantic models from manifest data to ensure robust schema
      validation and serialization.
    - Integrating with Django ORM models that represent llmhost manifests,
      supporting creation, update, deletion, and querying of database records.
    - Transforming data between Django ORM models and Pydantic models to enable
      seamless conversion between database and API representations.
    - Ensuring atomic and consistent application of changes using Django's
      transaction management.
    - Providing detailed logging and error handling integrated with the Smarter
      platform's diagnostics systems.

    This broker is a key component in the deployment, configuration, and
    lifecycle management of llmhosts in the Smarter Framework.
    """

    # override the base abstract manifest model with the LLMHost model
    _manifest: Optional[SAMLLMHost] = None
    _pydantic_model: Type[SAMLLMHost] = SAMLLMHost
    _llmhost: Optional[LLMHost] = None
    _name: Optional[str] = None
    _ready: bool = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        msg = f"{self.formatted_class_name}.__init__() broker for {self.kind} {self.name} is {self.ready_state}."
        logger.info(msg)

    @property
    def SerializerClass(self) -> Type[LLMHostSerializer]:
        """
        The Django ORM model serializer class for the LLMHost.

        :returns: The LLMHost Django ORM model serializer class.
        :rtype: Type[ModelSerializer]
        """
        return LLMHostSerializer

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
    def llmhost(self) -> Optional[LLMHost]:
        """
        Provides access to the Django ORM model instance representing the current Smarter LLMHost.

        :returns: The Django ORM LLMHost instance if found or created, otherwise ``None`` if neither
                  a database record nor a manifest is available.
        :rtype: Optional[LLMHost]

        .. admonition:: FIX NOTE

            This should be refactored/removed in favor of orm_instance. There is no logic
            in this property that merits it overriding the parent orm_instance property.

        .. admonition:: FIX NOTE

            This is breaking an unwritten rule of Smarter resources in that it is
            lazily **creating** a database record on a property getter.
            Creating/updating database records should be handled in apply().
        """
        if self._llmhost:
            return self._llmhost

        try:
            self._llmhost = LLMHost.get_cached_object(
                invalidate=True, user_profile=self.user_profile, name=self.name
            )  # type: ignore
            logger.debug(
                "%s.llmhost() retrieved existing LLMHost instance %s owned by %s from database.",
                self.formatted_class_name,
                self._llmhost,
                self.user_profile,
            )
            return self._llmhost
        except LLMHost.DoesNotExist:
            self._llmhost = None

        logger.debug(
            "%s.llmhost() LLMHost instance not found for user_profile %s. Attempting to create a new instance.",
            self.formatted_class_name,
            self.user_profile,
        )
        if self.manifest:
            data = self.manifest_to_django_orm()
            data["user_profile"] = self.user_profile
            logger.debug("%s.llmhost() Creating new LLMHost with data: %s", self.formatted_class_name, data)
            tags = data.pop("tags", [])
            self._llmhost = LLMHost.objects.create(**data)
            if self._llmhost and tags:
                self._llmhost.tags.set(tags)
            self._created = True
            logger.warning(
                "%s.llmhost() lazily created new LLMHost instance %s owned by %s. This logic should be handled in apply().",
                self.formatted_class_name,
                self._llmhost,
                self.user_profile,
            )
        else:
            logger.warning(
                "%s.llmhost() %s not found for user_profile %s",
                self.formatted_class_name,
                self._llmhost,
                self.user_profile,
            )

        return self._llmhost

    def manifest_to_django_orm(self) -> dict:
        """
        Convert the Smarter API LLMHost manifest into a dictionary suitable for creating or updating a Django ORM LLMHost model.

        :returns: A dictionary containing all fields required to create or update a Django ORM LLMHost model.
        :rtype: dict

        :raises SAMBrokerErrorNotReady: If the manifest is not loaded or cannot be found.
        :raises SAMLLMHostBrokerError: If the manifest configuration cannot be converted to a dictionary.
        """
        if not self.manifest:
            raise SAMBrokerErrorNotReady(
                f"Manifest not loaded for {self.kind} broker. Cannot convert to Django ORM.", thing=self.kind
            )
        metadata = super().manifest_to_django_orm()

        config_dump = self.manifest.spec.config.model_dump(mode="json")
        config_dump = self.to_snake_case(config_dump)
        if not isinstance(config_dump, dict):
            raise SAMLLMHostBrokerError(
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

    @camel_case()
    def django_orm_to_manifest_dict(self) -> Optional[dict]:
        """
        Transform the Django ORM LLMHost model instance into a dictionary compatible with the Smarter API LLMHost manifest format.

        :returns: A dictionary representing the Smarter API LLMHost manifest, or ``None`` if the LLMHost model is not set.
        :rtype: Optional[dict]

        :raises SAMLLMHostBrokerError: If the ORM model cannot be converted to a manifest dictionary.
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
        if not self.llmhost:
            logger.warning(
                "%s.django_orm_to_manifest_dict() called without a LLMHost. This could affect broker operations.",
                self.formatted_class_name,
            )
            return None
        llmhost_dict = model_to_dict(self.llmhost)
        llmhost_dict = self.to_camel_case(llmhost_dict)
        if not isinstance(llmhost_dict, dict):
            raise SAMLLMHostBrokerError(f"Failed to convert {self.kind} {self.llmhost.name} to dict", thing=self.kind)
        llmhost_dict.pop("id", None)
        llmhost_dict.pop("name", None)
        llmhost_dict.pop("description", None)
        llmhost_dict.pop("version", None)
        # fields owned by status, not spec — model_to_dict() pulls these in
        # via to_camel_case() but SAMLLMHostSpec doesn't accept them.
        for status_field in ("userProfile", "createdAt", "updatedAt", "recordLocator"):
            llmhost_dict.pop(status_field, None)

        meta = SAMLLMHostMetadata(
            name=self.llmhost.name,
            description=self.llmhost.description,
            version=self.llmhost.version,
            tags=self.llmhost.tags_list,
            annotations=self.llmhost.annotations if isinstance(self.llmhost.annotations, list) else [],
        )
        spec_config = SAMLLMHostSpecConfig(**llmhost_dict)
        spec = SAMLLMHostSpec(config=spec_config)
        status = SAMLLMHostStatus(
            accountNumber=self.account.account_number,
            username=self.user_profile.user.username,
            recordLocator=self.llmhost.record_locator,
            created=self.llmhost.created_at,
            modified=self.llmhost.updated_at,
        )
        model = SAMLLMHost(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=meta,
            spec=spec,
            status=status,
        )

        logger.debug(
            "%s.django_orm_to_manifest_dict() converted LLMHost %s to manifest dict: %s",
            self.formatted_class_name,
            self.llmhost.name,
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
        class_name = f"{SAMLLMHostBroker.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    @property
    def kind(self) -> str:
        """
        Returns the manifest kind for the Smarter API LLMHost.

        :returns: The manifest kind string for the Smarter API LLMHost.
        :rtype: str
        """
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMLLMHost]:
        """
        Returns the Smarter API LLMHost manifest as a Pydantic model.

        :returns: An instance of ``SAMLLMHost`` representing the llmhost manifest, or ``None``
                if the manifest cannot be initialized.
        :rtype: Optional[SAMLLMHost]
        """
        if self._manifest:
            if not isinstance(self._manifest, SAMLLMHost):
                raise SAMLLMHostBrokerError("Cached manifest is not a SAMLLMHost instance", thing=self.kind)
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            logger.debug(
                "%s.manifest() initializing %s from SAMLoader with name %s",
                self.formatted_class_name,
                self.kind,
                self.loader.manifest_metadata.get(SAMMetadataKeys.NAME.value, "unknown"),
            )
            self._manifest = SAMLLMHost(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMLLMHostMetadata(**self.loader.manifest_metadata),
                spec=SAMLLMHostSpec(**self.loader.manifest_spec),
            )
            return self._manifest
        if self._llmhost:
            self._manifest = self.django_orm_to_manifest_dict()  # type: ignore
            if self._manifest:
                logger.debug(
                    "%s.manifest() initialized from loader for existing LLMHost %s with name %s",
                    self.formatted_class_name,
                    self._llmhost,
                    self._llmhost.name,
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

        # 1.) invalidate the LLMHost cache itself.
        LLMHost.get_cached_object(pk=self.llmhost.id, invalidate=True)  # type: ignore

        # 2.) invalidate list-level caches for this user_profile.
        LLMHost.get_cached_objects(user_profile=self.user_profile, invalidate=True)

        return super().cache_invalidations()

    @property
    def ORMMetaModelClass(self) -> Type[LLMHost]:
        """
        Return the Django ORM meta model class for the broker.

        :return: The Django ORM meta model class definition for the broker.
        :rtype: Type[LLMHost]
        """
        return LLMHost

    @property
    def ORMModelClass(self) -> Type[LLMHost]:
        """
        The Django ORM model class for the LLMHost.

        :returns: The LLMHost Django ORM model class.
        :rtype: Type[LLMHost]
        """
        return LLMHost

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return an example manifest for the Smarter API LLMHost.

        :returns: A JSON response containing an example Smarter API LLMHost manifest.
        :rtype: SmarterJournaledJsonResponse
        """

        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)

        meta_data = SAMLLMHostMetadata(
            name="example_llmhost",
            description="This is an example llmhost manifest generated by the SAMLLMHostBroker. It serves as a template for creating your own llmhost manifests.",
            version="1.0.0",
            tags=["example", "template", "self-hosted"],
            annotations=[
                {"license": "apache-2.0"},
                {"family": "llama"},
            ],
        )
        url_adapter = TypeAdapter(HttpUrl)

        config = SAMLLMHostSpecConfig(
            provenance=SAMLLMHostProvenanceConfig(
                huggingfaceRepoId="meta-llama/Meta-Llama-3-8B-Instruct",
                huggingfaceRevision="5f0b02c75b57c5855da9ae460ce51323ea669d8",
                license="llama3",
                modelArchitecture="llama",
            ),
            characteristics=SAMLLMHostCharacteristicsConfig(
                parameterCount=8_000_000_000,
                contextWindow=8192,
                quantization=Quantization.AWQ,
                supportsStreaming=True,
                supportsFunctionCalling=True,
                supportsVision=False,
            ),
            serving=SAMLLMHostServingConfig(
                inferenceEngine=InferenceEngine.VLLM,
                apiFormat=ApiFormat.OPENAI_COMPATIBLE,
                endpointUrl=url_adapter.validate_python("https://llmhost.example.com/v1"),
                apiKey="smarter-secret://llmhost/example/api-key",
                engineConfig={
                    "tensor_parallel_size": 1,
                    "max_model_len": 8192,
                    "gpu_memory_utilization": 0.9,
                    "dtype": "auto",
                },
            ),
            infrastructure=SAMLLMHostInfrastructureConfig(
                deploymentType=DeploymentType.KUBERNETES,
                cloudProvider=CloudProvider.AWS,
                region="us-east-1",
                instanceType="g5.2xlarge",
                gpuType="A10G",
                gpuCount=1,
                vramRequiredGb=24,
                costPerHour=Decimal("1.2120"),
            ),
            healthCheck=SAMLLMHostHealthCheckConfig(
                healthCheckUrl=url_adapter.validate_python("https://llmhost.example.com/health"),
            ),
        )

        spec = SAMLLMHostSpec(config=config)
        status = SAMLLMHostStatus(
            accountNumber=smarter_cached_objects.smarter_account.account_number,
            username=smarter_cached_objects.smarter_admin.username,
            recordLocator="abc123def456",
            created=datetime.datetime.now(),
            modified=datetime.datetime.now(),
        )
        model = SAMLLMHost(apiVersion=self.api_version, kind=self.kind, metadata=meta_data, spec=spec, status=status)

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
            llmhosts = LLMHost.objects.filter(user_profile__account=self.account, name=name)
        else:
            llmhosts = LLMHost.objects.filter(user_profile__account=self.account)
        llmhosts = llmhosts.with_ownership_permission_for(self.user_profile.user).order_by("name")[:MAX_RESULTS]
        logger.debug(
            "%s.get() found %s LLMHosts for account %s", self.formatted_class_name, llmhosts.count(), self.account
        )

        for llmhost in llmhosts:
            try:
                model_dump = LLMHostSerializer(llmhost).data
                if not model_dump:
                    raise SAMLLMHostBrokerError(
                        f"Model dump failed for {self.kind} {llmhost.name}", thing=self.kind, command=command
                    )
                camel_cased_model_dump = self.to_camel_case(model_dump)
                data.append(camel_cased_model_dump)
            except Exception as e:
                logger.error(
                    "%s.get() failed to serialize %s %s",
                    self.formatted_class_name,
                    self.kind,
                    llmhost.name,
                    exc_info=True,
                )
                raise SAMLLMHostBrokerError(
                    f"Failed to serialize {self.kind} {llmhost.name}", thing=self.kind, command=command
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: name,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=LLMHostSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    # pylint: disable=too-many-branches
    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Apply the manifest.

        Copy the manifest data to the Django ORM model and save it. Fields that
        are readonly at the ORM level are stripped from the update dict before
        the save() call, since they're either DB-managed (id, timestamps) or
        handled through a different API (tags).
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
        if not isinstance(self.llmhost, LLMHost):
            raise SAMLLMHostBrokerError(f"LLMHost {self.name} not found", thing=self.kind, command=command)
        with transaction.atomic():
            readonly_fields = ["id", "created_at", "updated_at", "tags"]
            try:
                data = self.manifest_to_django_orm()
                tags = data.get("tags", [])
                for field in readonly_fields:
                    data.pop(field, None)
                for key, value in data.items():
                    setattr(self.llmhost, key, value)
                if self.llmhost.user_profile != self.user_profile:
                    raise SAMLLMHostBrokerError(
                        f"User profile mismatch for {self.kind} {self.manifest.metadata.name}",
                        thing=self.kind,
                        command=command,
                    )
                self.llmhost.save()

                # Fix note: occasionally seeing AttributeError: 'list' object has no attribute 'set'
                # in the logs, which is why this is wrapped in a try/except block.
                try:
                    if not isinstance(self.llmhost.tags, TaggableManager):
                        logger.warning(
                            "%s.apply() llmhost.tags is a list instead of a TaggableManager for %s %s owned by %s. This is unexpected and may indicate an issue with the LLMHost model definition or the database state. Tags=%s",
                            self.formatted_class_name,
                            self.kind,
                            self.manifest.metadata.name,
                            self.user_profile,
                            tags,
                        )
                    else:
                        self.llmhost.tags.set(tags)
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
                self.llmhost.refresh_from_db()
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
                raise SAMLLMHostBrokerError(
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
        if self.llmhost:
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
                raise SAMLLMHostBrokerError(
                    f"Failed to describe {self.kind} {self.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        if self.name is None:
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        if self.llmhost:
            try:
                self.llmhost.delete()
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
                raise SAMLLMHostBrokerError(
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
