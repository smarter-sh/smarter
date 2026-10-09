# pylint: disable=W0718,R0904
"""
Smarter API Budget Manifest handler.

A Budget is managed by superusers: only they may apply or delete one. Anyone may get and
describe the budgets that are attached to a resource that they may see.
"""

import datetime
from decimal import Decimal
from typing import Any, List, Optional, Type

from django.apps import apps
from django.db import transaction
from django.http import HttpRequest
from rest_framework.serializers import ModelSerializer

from smarter.apps.account.manifest.models.budget.const import MANIFEST_KIND
from smarter.apps.account.manifest.models.budget.metadata import SAMBudgetMetadata
from smarter.apps.account.manifest.models.budget.model import SAMBudget
from smarter.apps.account.manifest.models.budget.spec import (
    SAMBudgetSpec,
    SAMBudgetSpecConfig,
    SAMBudgetSpecResource,
)
from smarter.apps.account.manifest.models.budget.status import (
    SAMBudgetStatus,
    SAMBudgetStatusResource,
)
from smarter.apps.account.models import (
    Account,
    Budget,
    ResourceConstraint,
    UserProfile,
)
from smarter.apps.account.models.budget import is_visible, resolve_resource
from smarter.apps.account.serializers import BudgetSerializer
from smarter.apps.plugin.signals import broker_ready
from smarter.lib import logging
from smarter.lib.django.models import TimestampedModel
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
    __name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING, SmarterWaffleSwitches.MANIFEST_LOGGING]
)

MAX_RESULTS = 1000

CONFIG_FIELDS = {
    # manifest spec.config field: Django ORM Budget field
    "unit": "unit",
    "period": "period",
    "periodicLimit": "periodic_limit",
    "absoluteLimit": "absolute_limit",
    "duration": "duration",
    "action": "action",
    "warningThreshold": "warning_threshold",
    "message": "message",
}
"""The spec.config fields, and their Budget fields."""

RESOURCE_MODELS = {
    "ApiConnection": "connection.ApiConnection",
    "SqlConnection": "connection.SqlConnection",
    "LLMClient": "llmclient.LLMClient",
    "LLMHost": "llmhost.LLMHost",
    "LLMHostCompute": "llmhost.LLMHostCompute",
    "MCPClient": "mcpclient.MCPClient",
    "Orchestrator": "orchestrator.Orchestrator",
    "Provider": "provider.Provider",
    "Proxy": "proxy.Proxy",
    "Vectorsearch": "vectorsearch.Vectorsearch",
    "ApiPlugin": "plugin.PluginMeta",
    "SkillPlugin": "plugin.PluginMeta",
    "SqlPlugin": "plugin.PluginMeta",
    "StaticPlugin": "plugin.PluginMeta",
    "WebsearchPlugin": "plugin.PluginMeta",
    "ImageSearchPlugin": "plugin.PluginMeta",
}
"""The Django models of the kinds of resource, other than Account and User, that are owned by a user."""


class SAMBudgetBrokerError(SAMBrokerError):
    """Base exception for Smarter API Budget Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Budget Manifest Broker Error"


def resource_to_manifest(resource_locator: str) -> dict[str, Any]:
    """A resource as a spec.resources entry: its kind and name if it has them, else its record locator."""
    resource = resolve_resource(resource_locator)
    if isinstance(resource, Account):
        return {"kind": "Account", "name": resource.account_number}
    if isinstance(resource, UserProfile):
        return {
            "kind": "User",
            "name": resource.user.username,
            "accountNumber": resource.account.account_number,
        }
    if resource is not None and isinstance(getattr(resource, "user_profile", None), UserProfile):
        model_label = resource._meta.label  # pylint: disable=protected-access
        kind = getattr(resource, "kind", None) if model_label == "plugin.PluginMeta" else None
        kind = str(kind) if kind else next((k for k, label in RESOURCE_MODELS.items() if label == model_label), None)
        if kind:
            return {
                "kind": kind,
                "name": resource.name,  # type: ignore[attr-defined]
                "accountNumber": resource.user_profile.account.account_number,  # type: ignore[attr-defined]
            }
    return {"recordLocator": resource_locator}


class SAMBudgetBroker(AbstractBroker):
    """
    Broker for :py:class:`SAM <smarter.lib.manifest.models.AbstractSAMMetadataBase>` Budget manifests.

    The broker converts between Budget manifests and the
    :class:`~smarter.apps.account.models.Budget` Django ORM model and its
    :class:`~smarter.apps.account.models.ResourceConstraint` attachments, and implements the
    ``smarter`` CLI commands for Budgets: ``apply``, ``describe``, ``get``, ``delete`` and
    ``example_manifest``. ``spec.resources`` is declarative: applying a manifest attaches the
    budget to the resources that it lists, and detaches it from the others.
    """

    _manifest: Optional[SAMBudget] = None
    _pydantic_model: Type[SAMBudget] = SAMBudget
    _budget: Optional[Budget] = None
    _name: Optional[str] = None
    _ready: bool = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        logger.info(
            "%s.__init__() broker for %s %s is %s.", self.formatted_class_name, self.kind, self.name, self.ready_state
        )

    @property
    def SerializerClass(self) -> Type[ModelSerializer]:
        """The Django ORM model serializer class for the Budget."""
        return BudgetSerializer

    @property
    def ready(self) -> bool:
        """A broker is ready if it has a manifest, or an account."""
        if self._ready:
            return self._ready
        if self.manifest is not None or self.account is not None:
            self._ready = True
            broker_ready.send(sender=self.__class__, broker=self)
        return self._ready

    @property
    def orm_meta_instance(self) -> Optional[Budget]:  # type: ignore[override]
        """The Budget.

        Budgets are not owned, so the base class's lookup by owner does not apply.
        """
        return self.budget

    @property
    def orm_instance(self) -> Optional[Budget]:  # type: ignore[override]
        return self.budget

    @property
    def is_superuser(self) -> bool:
        return bool(self.user_profile and self.user_profile.user.is_superuser)

    @property
    def budget(self) -> Optional[Budget]:
        """The Budget with the broker's name, if it exists.

        It is never created here: :meth:`apply` does that.
        """
        if self._budget:
            return self._budget
        if not self.name:
            return None
        self._budget = Budget.objects.filter(name=self.name).first()
        return self._budget

    def is_visible_budget(self, budget: Budget) -> bool:
        """Superusers see every budget.

        Others see those attached to a resource that they may see.
        """
        if self.is_superuser:
            return True
        if not self.user_profile:
            return False
        return any(
            is_visible(self.user_profile, locator)
            for locator in budget.constraints.values_list("resource_locator", flat=True)  # type: ignore[attr-defined]
        )

    # -------------------------------------------------------------------------
    # resources
    # -------------------------------------------------------------------------
    def resolve_account(self, account_number: Optional[str]) -> Account:
        if not account_number:
            if not self.account:
                raise SAMBudgetBrokerError("An accountNumber is required.", thing=self.kind)
            return self.account
        account = Account.objects.filter(account_number=account_number).first()
        if account is None:
            raise SAMBudgetBrokerError(f"Account {account_number} not found.", thing=self.kind)
        return account

    def resolve_locator(self, resource: SAMBudgetSpecResource) -> str:
        """The record locator of a spec.resources entry."""
        if resource.recordLocator:
            if resolve_resource(resource.recordLocator) is None:
                raise SAMBudgetBrokerError(f"Resource {resource.recordLocator} not found.", thing=self.kind)
            return resource.recordLocator
        if resource.kind == "Account":
            account = Account.objects.filter(account_number=resource.name).first()
            if account is None:
                raise SAMBudgetBrokerError(f"Account {resource.name} not found.", thing=self.kind)
            return account.record_locator
        account = self.resolve_account(resource.accountNumber)
        if resource.kind == "User":
            user_profile = UserProfile.objects.filter(user__username=resource.name, account=account).first()
            if user_profile is None:
                raise SAMBudgetBrokerError(
                    f"User {resource.name} not found in account {account.account_number}.", thing=self.kind
                )
            return user_profile.record_locator
        model: Type[TimestampedModel] = apps.get_model(RESOURCE_MODELS[resource.kind])  # type: ignore[index]
        instance = model.objects.filter(name=resource.name, user_profile__account=account).order_by("pk").first()  # type: ignore[attr-defined]
        if instance is None:
            raise SAMBudgetBrokerError(
                f"{resource.kind} {resource.name} not found in account {account.account_number}.", thing=self.kind
            )
        return instance.record_locator

    # -------------------------------------------------------------------------
    # conversions
    # -------------------------------------------------------------------------
    def manifest_to_django_orm(self) -> dict[str, Any]:
        """
        Convert the manifest into a dict of Django ORM Budget fields.

        :raises SAMBrokerErrorNotReady: If the manifest is not loaded.
        """
        if not self.manifest:
            raise SAMBrokerErrorNotReady(f"Manifest not loaded for {self.kind} broker.", thing=self.kind)
        config = self.manifest.spec.config
        retval = {**super().manifest_to_django_orm()}
        retval.pop("user_profile", None)
        for manifest_field, orm_field in CONFIG_FIELDS.items():
            retval[orm_field] = getattr(config, manifest_field)
        retval["message"] = retval["message"] or ""
        return retval

    def status_for(self, budget: Budget) -> list[dict[str, Any]]:
        """The budget versus the actual spending of each resource that the user may see."""
        retval = []
        for constraint in budget.constraints.select_related("budget").order_by("resource_locator"):  # type: ignore[attr-defined]
            if not self.is_superuser and not (
                self.user_profile and is_visible(self.user_profile, constraint.resource_locator)
            ):
                continue
            status = constraint.status()
            retval.append(
                SAMBudgetStatusResource(
                    recordLocator=constraint.resource_locator,
                    isActive=constraint.is_active,
                    startDate=constraint.start_date,
                    expiresAt=status["expires_at"],
                    periodicActual=status["periodic_actual"],
                    periodicPercent=status["periodic_percent"],
                    absoluteActual=status["absolute_actual"],
                    absolutePercent=status["absolute_percent"],
                    isLocked=status["is_locked"],
                    lockReason=status["lock_reason"],
                ).model_dump()
            )
        return retval

    def django_orm_to_manifest_dict(self) -> Optional[dict]:
        """Convert the Budget into a manifest dict, with its status."""
        budget = self.budget
        if not budget:
            return None
        config = {manifest_field: getattr(budget, orm_field) for manifest_field, orm_field in CONFIG_FIELDS.items()}
        config["message"] = config["message"] or None
        locators = budget.constraints.filter(is_active=True).values_list("resource_locator", flat=True)  # type: ignore[attr-defined]
        resources = [
            SAMBudgetSpecResource(**resource_to_manifest(locator))
            for locator in locators
            if self.is_superuser or (self.user_profile and is_visible(self.user_profile, locator))
        ]
        meta = SAMBudgetMetadata(
            name=budget.name,
            description=budget.description,
            version=budget.version,
            tags=budget.tags_list,
            annotations=budget.annotations if isinstance(budget.annotations, list) else [],
        )
        status = SAMBudgetStatus(
            recordLocator=budget.record_locator,
            created=budget.created_at,
            modified=budget.updated_at,
            resources=self.status_for(budget),  # type: ignore[arg-type]
        )
        model = SAMBudget(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=meta,
            spec=SAMBudgetSpec(config=SAMBudgetSpecConfig(**config), resources=resources),
            status=status,
        )
        return model.model_dump()

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def formatted_class_name(self) -> str:
        """The class name, for logging."""
        return self.formatted_text(f"{SAMBudgetBroker.__name__}[{id(self)}]")

    @property
    def kind(self) -> str:
        """The manifest kind: Budget."""
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMBudget]:
        """The Budget manifest, as a Pydantic model, from the manifest loader."""
        if self._manifest:
            if not isinstance(self._manifest, SAMBudget):
                raise SAMBudgetBrokerError("Cached manifest is not a SAMBudget instance", thing=self.kind)
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMBudget(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMBudgetMetadata(**self.loader.manifest_metadata),
                spec=SAMBudgetSpec(**self.loader.manifest_spec),
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    @property
    def ORMMetaModelClass(self) -> Type[Budget]:  # type: ignore[override]
        return Budget

    @property
    def ORMModelClass(self) -> Type[Budget]:  # type: ignore[override]
        return Budget

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return an example Budget manifest: a monthly allowance for a student."""
        command = SmarterJournalCliCommands(self.example_manifest.__name__)
        meta_data = SAMBudgetMetadata(
            name="student_monthly_allowance",
            description="Each student may spend $10 a month on AI, and $100 in total.",
            version="1.0.0",
            tags=["example", "education"],
            annotations=[{"smarter.sh/budget/purpose": "example"}],
        )
        config = SAMBudgetSpecConfig(
            unit="cost",
            period="month",
            periodicLimit=Decimal("10.00"),
            absoluteLimit=Decimal("100.00"),
            action="block",
            warningThreshold=80,
            message="You have used this month's AI allowance. It renews on the 1st of next month.",
        )
        resources = [
            SAMBudgetSpecResource(kind="User", name="student1"),
            SAMBudgetSpecResource(kind="LLMClient", name="stackademy_sql"),
        ]
        status = SAMBudgetStatus(
            recordLocator="budget-abc123",
            created=datetime.datetime.now(),
            modified=datetime.datetime.now(),
        )
        model = SAMBudget(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=meta_data,
            spec=SAMBudgetSpec(config=config, resources=resources),
            status=status,
        )
        return self.json_response_ok(command=command, data=model.model_dump())

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return the Budgets that the user may see, optionally filtered by name."""
        command = SmarterJournalCliCommands(self.get.__name__)
        name = self.clean_cli_param(
            param=kwargs.get(SAMMetadataKeys.NAME.value, None),
            param_name="name",
            url=self.smarter_build_absolute_uri(request),
        )
        if self.user_profile is None:
            raise SAMBrokerErrorNotReady("user_profile is not set.")
        budgets = Budget.objects.all()
        if name:
            budgets = budgets.filter(name=name)
        data = [
            self.to_camel_case(BudgetSerializer(budget).data)
            for budget in budgets.order_by("name")[:MAX_RESULTS]
            if self.is_visible_budget(budget)
        ]
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: name,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=BudgetSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Create or update the Budget from the manifest, then attach it to spec.resources, and detach it from the others.

        Only superusers may apply a Budget.
        """
        command = SmarterJournalCliCommands(self.apply.__name__)
        if not self.ready or not self.manifest:
            raise SAMBrokerErrorNotReady(
                f"{self.kind} {self.name} broker is not ready", thing=self.kind, command=command
            )
        if not self.is_superuser:
            raise SAMBudgetBrokerError(f"Only superusers may apply a {self.kind}.", thing=self.kind, command=command)
        data = self.manifest_to_django_orm()
        tags = data.pop("tags", None) or []
        for field in ("id", "created_at", "updated_at"):
            data.pop(field, None)
        locators = list(dict.fromkeys(self.resolve_locator(resource) for resource in self.manifest.spec.resources))
        with transaction.atomic():
            budget = self.budget
            if budget is None:
                budget = Budget(**data)
            else:
                for key, value in data.items():
                    setattr(budget, key, value)
            try:
                budget.save()
                budget.tags.set(tags)
                ResourceConstraint.objects.filter(budget=budget).exclude(resource_locator__in=locators).delete()
                for locator in locators:
                    budget.attach(locator)
            except Exception as e:
                raise SAMBudgetBrokerError(
                    f"Failed to apply {self.kind} {self.manifest.metadata.name}: {e}", thing=self.kind, command=command
                ) from e
        self._budget = budget
        self.cache_invalidations()
        return self.json_response_ok(command=command, data=self.to_json())

    def prompt(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = SmarterJournalCliCommands(self.prompt.__name__)
        raise SAMBrokerErrorNotImplemented(message="Prompt not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return the Budget as a manifest, with the budget versus the actual spending of each resource."""
        command = SmarterJournalCliCommands(self.describe.__name__)
        if self.name is None:
            raise SAMBrokerErrorNotReady(f"{self.kind} name property is not set.", thing=self.kind, command=command)
        if not self.budget or not self.is_visible_budget(self.budget):
            raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        try:
            data = self.django_orm_to_manifest_dict()
        except Exception as e:
            raise SAMBudgetBrokerError(
                f"Failed to describe {self.kind} {self.name}: {e}", thing=self.kind, command=command
            ) from e
        return self.json_response_ok(command=command, data=data)

    @memoized_dependencies
    def dependencies(self) -> List[AbstractBroker]:
        """Return brokers for the resources that depend on this Budget.

        No resource refers to a Budget. A Budget refers to the resources that it constrains, and deleting
        it detaches it from them.

        :return: An empty list.
        :rtype: List[AbstractBroker]
        """
        return []

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Delete the Budget, which detaches it from its resources and removes their locks.

        Superusers only.
        """
        command = SmarterJournalCliCommands(self.delete.__name__)
        if self.name is None or not self.budget or not self.is_visible_budget(self.budget):
            raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        if not self.is_superuser:
            raise SAMBudgetBrokerError(f"Only superusers may delete a {self.kind}.", thing=self.kind, command=command)
        self.verify_no_dependencies(command)
        try:
            self.budget.delete()
            self._budget = None
            self.cache_invalidations()
        except Exception as e:
            raise SAMBudgetBrokerError(
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


__all__ = ["SAMBudgetBroker", "SAMBudgetBrokerError"]
