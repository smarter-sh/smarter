# pylint: disable=W0718
"""
Smarter API CustomDomain Manifest handler.

A CustomDomain is a domain name that serves LLMClients from the customer's own
brand. ``apply`` creates the Smarter resource; ``deploy`` registers the domain
with AWS: a Route53 hosted zone, and a TLS certificate, which the
:func:`~smarter.apps.llmclient.tasks.register_custom_domain` Celery task creates.
"""

import datetime
from typing import Any, List, Optional, Type

from django.db import transaction
from django.http import HttpRequest
from rest_framework.serializers import ModelSerializer

from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llmclient.manifest.models.custom_domain.const import MANIFEST_KIND
from smarter.apps.llmclient.manifest.models.custom_domain.metadata import (
    SAMCustomDomainMetadata,
)
from smarter.apps.llmclient.manifest.models.custom_domain.model import (
    SAMCustomDomain,
)
from smarter.apps.llmclient.manifest.models.custom_domain.spec import (
    SAMCustomDomainSpec,
    SAMCustomDomainSpecConfig,
)
from smarter.apps.llmclient.manifest.models.custom_domain.status import (
    SAMCustomDomainStatus,
)
from smarter.apps.llmclient.models import (
    LLMClientCustomDomain,
    LLMClientCustomDomainDNS,
)
from smarter.apps.llmclient.serializers import LLMClientCustomDomainListSerializer
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
    __name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING, SmarterWaffleSwitches.MANIFEST_LOGGING]
)

MAX_RESULTS = 1000


class SAMCustomDomainBrokerError(SAMBrokerError):
    """Base exception for Smarter API CustomDomain Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API CustomDomain Manifest Broker Error"


class SAMCustomDomainBroker(AbstractBroker):
    """
    Broker for :py:class:`SAM <smarter.lib.manifest.models.AbstractSAMMetadataBase>` CustomDomain manifests.

    The broker converts between CustomDomain manifests and the
    :class:`~smarter.apps.llmclient.models.LLMClientCustomDomain` Django ORM model, and implements
    the ``smarter`` CLI commands for CustomDomains: ``apply``, ``describe``, ``get``, ``delete``,
    ``deploy`` and ``example_manifest``. ``deploy`` registers the domain with AWS Route53.
    ``undeploy`` is not implemented: Smarter does not delete hosted zones.
    An LLMClient uses a CustomDomain with its ``spec.customDomain``.
    """

    _manifest: Optional[SAMCustomDomain] = None
    _pydantic_model: Type[SAMCustomDomain] = SAMCustomDomain
    _custom_domain: Optional[LLMClientCustomDomain] = None
    _name: Optional[str] = None
    _ready: bool = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        logger.info(
            "%s.__init__() broker for %s %s is %s.", self.formatted_class_name, self.kind, self.name, self.ready_state
        )

    @property
    def SerializerClass(self) -> Type[ModelSerializer]:
        """The Django ORM model serializer class for the CustomDomain."""
        return LLMClientCustomDomainListSerializer

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
    def custom_domain(self) -> Optional[LLMClientCustomDomain]:
        """The user's CustomDomain with the broker's name, if it exists.

        It is never created here: :meth:`apply` does that.
        """
        if self._custom_domain:
            return self._custom_domain
        if not self.user_profile or not self.name:
            return None
        self._custom_domain = LLMClientCustomDomain.objects.filter(
            user_profile=self.user_profile, name=self.name
        ).first()
        return self._custom_domain

    def manifest_to_django_orm(self) -> dict[str, Any]:
        """
        Convert the manifest into a dict of Django ORM LLMClientCustomDomain fields.

        :raises SAMBrokerErrorNotReady: If the manifest is not loaded.
        """
        if not self.manifest:
            raise SAMBrokerErrorNotReady(f"Manifest not loaded for {self.kind} broker.", thing=self.kind)
        retval = {**super().manifest_to_django_orm()}
        retval["domain_name"] = self.manifest.spec.config.domainName
        return retval

    def django_orm_to_manifest_dict(self) -> Optional[dict]:
        """Convert the CustomDomain into a manifest dict, with its status."""
        if not self.account or not self.user_profile:
            raise SAMBrokerErrorNotReady(
                f"Account and user profile are required to describe a {self.kind}.", thing=self.kind
            )
        custom_domain = self.custom_domain
        if not custom_domain:
            return None
        meta = SAMCustomDomainMetadata(
            name=custom_domain.name,
            description=custom_domain.description,
            version=custom_domain.version,
            tags=custom_domain.tags_list,
            annotations=custom_domain.annotations if isinstance(custom_domain.annotations, list) else [],
        )
        spec = SAMCustomDomainSpec(config=SAMCustomDomainSpecConfig(domainName=custom_domain.domain_name))
        dns_records = [
            f"{record.record_name} {record.record_ttl} {record.record_type} {record.record_value}"
            for record in LLMClientCustomDomainDNS.objects.filter(custom_domain=custom_domain).order_by("record_name")
        ]
        status = SAMCustomDomainStatus(
            accountNumber=self.account.account_number,
            username=self.user_profile.user.username,
            recordLocator=custom_domain.record_locator,
            created=custom_domain.created_at,
            modified=custom_domain.updated_at,
            awsHostedZoneId=custom_domain.aws_hosted_zone_id or None,
            verificationStatus=custom_domain.verification_status,
            verifiedAt=custom_domain.verified_at,
            verificationMessage=custom_domain.verification_message or None,
            dnsRecords=dns_records,
        )
        model = SAMCustomDomain(apiVersion=self.api_version, kind=self.kind, metadata=meta, spec=spec, status=status)
        return model.model_dump()

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def formatted_class_name(self) -> str:
        """The class name, for logging."""
        return self.formatted_text(f"{SAMCustomDomainBroker.__name__}[{id(self)}]")

    @property
    def kind(self) -> str:
        """The manifest kind: CustomDomain."""
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMCustomDomain]:
        """The CustomDomain manifest, as a Pydantic model, from the manifest loader."""
        if self._manifest:
            if not isinstance(self._manifest, SAMCustomDomain):
                raise SAMCustomDomainBrokerError("Cached manifest is not a SAMCustomDomain instance", thing=self.kind)
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMCustomDomain(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMCustomDomainMetadata(**self.loader.manifest_metadata),
                spec=SAMCustomDomainSpec(**self.loader.manifest_spec),
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def cache_invalidations(self) -> None:
        """Invalidate the cached CustomDomain, and the user's cached CustomDomain lists."""
        if self.custom_domain:
            LLMClientCustomDomain.get_cached_object(pk=self.custom_domain.pk, invalidate=True)
        if self.user_profile:
            LLMClientCustomDomain.get_cached_objects(user_profile=self.user_profile, invalidate=True)
        return super().cache_invalidations()

    @property
    def ORMMetaModelClass(self) -> Type[LLMClientCustomDomain]:
        return LLMClientCustomDomain

    @property
    def ORMModelClass(self) -> Type[LLMClientCustomDomain]:
        return LLMClientCustomDomain

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return an example CustomDomain manifest."""
        command = SmarterJournalCliCommands(self.example_manifest.__name__)
        meta_data = SAMCustomDomainMetadata(
            name="example_custom_domain",
            description="Serves the company's LLMClients from llmclients.example.com.",
            version="1.0.0",
            tags=["example"],
            annotations=[{"smarter.sh/custom-domain/purpose": "example"}],
        )
        status = SAMCustomDomainStatus(
            accountNumber=smarter_cached_objects.smarter_account.account_number,
            username=smarter_cached_objects.smarter_admin.username,
            recordLocator="abc123def456",
            created=datetime.datetime.now(),
            modified=datetime.datetime.now(),
            awsHostedZoneId="Z0123456789ABCDEFGHIJ",
            verificationStatus="Verifying",
            verificationMessage="The NS records of llmclients.example.com are not delegated to Smarter yet.",
            dnsRecords=["llmclients.example.com 172800 NS ns-123.awsdns-45.com."],
        )
        model = SAMCustomDomain(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=meta_data,
            spec=SAMCustomDomainSpec(config=SAMCustomDomainSpecConfig(domainName="llmclients.example.com")),
            status=status,
        )
        return self.json_response_ok(command=command, data=model.model_dump())

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return the CustomDomains that the user may read, optionally filtered by name."""
        command = SmarterJournalCliCommands(self.get.__name__)
        name = self.clean_cli_param(
            param=kwargs.get(SAMMetadataKeys.NAME.value, None),
            param_name="name",
            url=self.smarter_build_absolute_uri(request),
        )
        if self.user_profile is None:
            raise SAMBrokerErrorNotReady("user_profile is not set.")
        custom_domains = LLMClientCustomDomain.objects.with_read_permission_for(self.user_profile.user)  # type: ignore[attr-defined]
        if name:
            custom_domains = custom_domains.filter(name=name)
        data = [
            self.to_camel_case(LLMClientCustomDomainListSerializer(custom_domain).data)
            for custom_domain in custom_domains.order_by("name")[:MAX_RESULTS]
        ]
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: name,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(
                    serializer=LLMClientCustomDomainListSerializer()
                ),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Create or update the CustomDomain from the manifest.

        The domain name of a CustomDomain that is registered, i.e. that has an AWS Route53
        hosted zone, cannot be changed.

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
        custom_domain = self.custom_domain
        if (
            custom_domain is not None
            and custom_domain.aws_hosted_zone_id
            and custom_domain.domain_name != data["domain_name"]
        ):
            raise SAMCustomDomainBrokerError(
                f"{self.kind} {self.name} is registered as {custom_domain.domain_name}, so its domainName cannot be changed.",
                thing=self.kind,
                command=command,
            )
        with transaction.atomic():
            if custom_domain is None:
                custom_domain = LLMClientCustomDomain(**data)
            else:
                for key, value in data.items():
                    setattr(custom_domain, key, value)
            try:
                custom_domain.save()
                custom_domain.tags.set(tags)
            except Exception as e:
                raise SAMCustomDomainBrokerError(
                    f"Failed to apply {self.kind} {self.manifest.metadata.name}: {e}", thing=self.kind, command=command
                ) from e
        self._custom_domain = custom_domain
        self.cache_invalidations()
        return self.json_response_ok(command=command, data=self.to_json())

    def prompt(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = SmarterJournalCliCommands(self.prompt.__name__)
        raise SAMBrokerErrorNotImplemented(message="Prompt not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return the CustomDomain as a manifest, with its status."""
        command = SmarterJournalCliCommands(self.describe.__name__)
        if self.name is None:
            raise SAMBrokerErrorNotReady(f"{self.kind} name property is not set.", thing=self.kind, command=command)
        if not self.custom_domain:
            raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        try:
            data = self.django_orm_to_manifest_dict()
        except Exception as e:
            raise SAMCustomDomainBrokerError(
                f"Failed to describe {self.kind} {self.name}: {e}", thing=self.kind, command=command
            ) from e
        return self.json_response_ok(command=command, data=data)

    @memoized_dependencies
    def dependencies(self) -> List[AbstractBroker]:
        """Return a broker for the LLMClient that uses this CustomDomain.

        LLMClient.custom_domain cascades deletes, so a CustomDomain cannot be deleted while
        an LLMClient uses it.

        :return: A broker for the LLMClient whose ``custom_domain`` is this CustomDomain.
        :rtype: List[AbstractBroker]
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.api.v1.manifests.enum import SAMKinds
        from smarter.apps.llmclient.models import LLMClient

        custom_domain = self.custom_domain
        if not custom_domain:
            return []
        return self.dependency_brokers(SAMKinds.LLM_CLIENT.value, LLMClient.objects.filter(custom_domain=custom_domain))

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Delete the CustomDomain.

        Refused while an LLMClient uses it. Its AWS Route53 hosted zone, if any, is not deleted.
        """
        command = SmarterJournalCliCommands(self.delete.__name__)
        if self.name is None or not self.custom_domain:
            raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        self.verify_no_dependencies(command)
        try:
            self.cache_invalidations()
            self.custom_domain.delete()
            self._custom_domain = None
        except Exception as e:
            raise SAMCustomDomainBrokerError(
                f"Failed to delete {self.kind} {self.name}", thing=self.kind, command=command
            ) from e
        return self.json_response_ok(command=command, data={})

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Register the CustomDomain with AWS: queue the register_custom_domain Celery task, which creates its Route53 hosted zone and TLS certificate.

        The domain is verified once its NS records, reported in ``status.dnsRecords``, are added to the root
        domain's DNS settings.
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.llmclient.tasks import register_custom_domain

        command = SmarterJournalCliCommands(self.deploy.__name__)
        if self.name is None or not self.custom_domain:
            raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        if not self.account:
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} has no account.", thing=self.kind, command=command)
        register_custom_domain.delay(account_id=self.account.id, domain_name=self.custom_domain.domain_name)
        return self.json_response_ok(
            command=command,
            data={"message": f"{self.kind} {self.name} ({self.custom_domain.domain_name}) is being registered."},
        )

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = SmarterJournalCliCommands(self.undeploy.__name__)
        raise SAMBrokerErrorNotImplemented(
            message=f"{self.kind} {self.name} undeploy() is not implemented.", thing=self.kind, command=command
        )

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = SmarterJournalCliCommands(self.logs.__name__)
        return self.json_response_ok(command=command, data={})
