"""
The detail of one Smarter resource, for the web console's resource lists.

Each list of the web console (see :class:`smarter.lib.django.listview.SmarterListApiView`) opens a resource's
detail when one of its rows is chosen. Besides the row's own fields, the detail shows:

- **its manifest**, as YAML, as ``smarter describe`` returns it;
- **its hierarchy**: the tree of every resource that it uses, recursively
  (:meth:`~smarter.lib.manifest.broker.AbstractBroker.dependency_tree`);
- **its dependents**: the resources that use it, and that keep it from being deleted
  (:meth:`~smarter.lib.manifest.broker.AbstractBroker.dependents`).

A resource is identified by its SAM kind and its record locator, e.g. ``Guardrail`` and ``guardrail-rMTAwx``.
Each row of a list has the url of its detail, its ``detail_url``, which
:class:`smarter.apps.account.serializers.MetaDataWithOwnershipModelSerializer` adds.
"""

import functools
import json
from typing import Optional

import yaml
from django.apps import apps
from django.db import models
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from smarter.apps.api.v1.cli.brokers import Brokers
from smarter.lib import logging
from smarter.lib.django.listview import ListviewPageRequest
from smarter.lib.manifest.models import SAMDependencyTreeNode
from smarter.lib.manifest.record_locator import (
    console_url,
    parse_record_locator,
    record_locator_prefix,
)

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)


class ResourceDetail(BaseModel):
    """The detail of one resource: its manifest, the resources that it uses, and those that use it."""

    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
    )

    kind: str = Field(..., description="The resource's SAM kind, e.g. Guardrail.")
    name: Optional[str] = Field(default=None, description="The resource's name.")
    record_locator: str = Field(..., description="The resource's record locator, e.g. guardrail-rMTAwx.")
    url: Optional[str] = Field(
        default=None, description="The resource's manifest page in the web console, where its manifest can be edited."
    )
    manifest: Optional[str] = Field(default=None, description="The resource's manifest, as YAML, or None on error.")
    manifest_error: str = Field(default="", description="Why the manifest could not be read, or an empty string.")
    tree: SAMDependencyTreeNode = Field(..., description="The resource, and every resource that it uses, recursively.")
    dependents: list[SAMDependencyTreeNode] = Field(
        default_factory=list,
        description=(
            "The resources that use this one, without their own children. One that the user may not read "
            "is locked: it has its kind and record locator only."
        ),
    )


def resource_detail_url(kind: Optional[str], record_locator: Optional[str]) -> Optional[str]:
    """
    Return the url of a resource's detail, from its kind and record locator.

    The list api serializers (:class:`smarter.apps.account.serializers.MetaDataWithOwnershipModelSerializer`) and
    the REST api's contract models send it as ``detailUrl``.

    .. code-block:: python

        resource_detail_url("Guardrail", "guardrail-rMTAwx")
        # '/dashboard/api/resource/Guardrail/guardrail-rMTAwx/'

    :param kind: The resource's SAM kind, e.g. ``Guardrail``.
    :type kind: Optional[str]
    :param record_locator: The resource's record locator.
    :type record_locator: Optional[str]
    :returns: The url, or None if either is missing.
    :rtype: Optional[str]
    """
    # the dashboard's urls import views that import the serializers. pylint: disable=import-outside-toplevel
    from django.conf import settings

    from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames
    from smarter.apps.dashboard.views.views.urls import DashboardReverseNames
    from smarter.lib.django.shortcuts import reverse

    if not kind or not record_locator:
        return None
    return reverse(
        f"{DashboardReverseNames.namespace}:{DashboardApiReverseNames.namespace}:"
        f"{DashboardApiReverseNames.resource_detail}",
        kwargs={"kind": str(kind), "record_locator": record_locator},
        urlconf=settings.ROOT_URLCONF,
    )


@functools.cache
def models_by_record_locator_prefix() -> dict[str, type[models.Model]]:
    """
    Return each Django model that has record locators, by the prefix of its record locators.

    A model has record locators when it has ``get_object_by_locator()``, as every
    :class:`~smarter.lib.django.models.timestamped_model.TimestampedModel` has. The installed models don't
    change while the process runs, so the map is computed once per process.

    :returns: The models, e.g. ``{"guardrail": Guardrail, ...}``.
    :rtype: dict[str, type[models.Model]]
    """
    return {
        record_locator_prefix(model): model
        for model in apps.get_models()
        if callable(getattr(model, "get_object_by_locator", None))
    }


def readable_instance(user, record_locator: str) -> Optional[models.Model]:
    """
    Return the resource of a record locator, if the user may read it.

    :param user: The authenticated user.
    :param record_locator: The resource's record locator, e.g. ``guardrail-rMTAwx``.
    :type record_locator: str
    :returns: The resource's Django ORM instance, or None if there is none, or the user may not read it.
    :rtype: Optional[models.Model]
    """
    try:
        prefix, _ = parse_record_locator(record_locator)
    except ValueError:
        return None
    model = models_by_record_locator_prefix().get(prefix)
    if model is None:
        return None
    instance = model.get_object_by_locator(record_locator)  # type: ignore[attr-defined]
    if instance is None:
        return None
    manager = type(instance)._default_manager  # pylint: disable=protected-access
    if hasattr(manager, "with_read_permission_for"):
        if not manager.filter(pk=instance.pk).with_read_permission_for(user).exists():  # type: ignore[attr-defined]
            return None
    return instance


def instance_of_kind(broker, kind: str, instance: models.Model) -> Optional[models.Model]:
    """
    Return a resource as a row of a kind's model, or None if it is not of the kind.

    The kind and the record locator of a detail's url are separate, so a url could pair a resource with
    another kind, whose broker would then find a different resource by the same name. A resource of the kind
    is a row of its broker's model, or of its meta model (a plugin's PluginMeta). A row of a parent model of
    the kind's model, e.g. the ConnectionBase of an SqlConnection, which a list may show, is the kind's row of
    the same primary key, if it has one.

    :param broker: A broker of the kind.
    :type broker: AbstractBroker
    :param kind: The SAM kind, e.g. ``Guardrail``.
    :type kind: str
    :param instance: The resource's Django ORM instance.
    :type instance: models.Model
    :returns: The resource's row of the kind's model, or None.
    :rtype: Optional[models.Model]
    """
    own_kind = getattr(instance, "kind", None)
    own_kind = getattr(own_kind, "value", own_kind)
    if isinstance(own_kind, str) and own_kind and Brokers.get_broker(own_kind) is not Brokers.get_broker(kind):
        return None
    model_classes: list[type[models.Model]] = []
    for attribute in ("ORMMetaModelClass", "ORMModelClass"):
        try:
            model_class = getattr(broker, attribute)
        # a broker that doesn't implement one of them. pylint: disable=W0718
        except Exception:
            continue
        if isinstance(model_class, type) and issubclass(model_class, models.Model):
            model_classes.append(model_class)
    for model_class in model_classes:
        if isinstance(instance, model_class):
            return instance
    for model_class in model_classes:
        if issubclass(model_class, type(instance)):
            return model_class._default_manager.filter(pk=instance.pk).first()  # pylint: disable=protected-access
    return None


def manifest_yaml(kind: str, instance: models.Model) -> tuple[Optional[str], str]:
    """
    Return a resource's manifest, as YAML, as ``smarter describe`` returns it to its owner.

    The resource is described on behalf of its owner, as the web console's manifest pages do, because a
    broker finds a resource by its name among those of its own user. The caller has already checked that
    the user may read it (see :func:`readable_instance`).

    :param kind: The resource's SAM kind.
    :type kind: str
    :param instance: The resource's Django ORM instance, which has a ``user_profile`` and a ``name``.
    :type instance: models.Model
    :returns: The manifest, and an empty string, or None and why it could not be read.
    :rtype: tuple[Optional[str], str]
    """
    broker_class = Brokers.get_broker(kind)
    owner = getattr(getattr(instance, "user_profile", None), "user", None)
    name = getattr(instance, "name", None)
    if broker_class is None or owner is None or not name:
        return None, f"A {kind} has no manifest."
    request = ListviewPageRequest(owner)
    try:
        broker = broker_class(request, name=name, kind=kind)
        response = broker.describe(request)
        data = json.loads(response.content).get("data")
    # a broken resource must not break its detail: its other tabs still work. pylint: disable=W0718
    except Exception as e:
        logger.warning("%s.manifest_yaml() could not describe %s %s: %s", logger_prefix, kind, name, e)
        return None, str(e)
    if not isinstance(data, dict):
        return None, f"The {kind} {name} has no manifest."
    return yaml.safe_dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True), ""


def resource_detail(request, kind: str, record_locator: str) -> Optional[ResourceDetail]:
    """
    Return the detail of a resource that the request's user may read.

    The hierarchy and the dependents are built by a broker of the user's own request, so that a resource that
    the user may not read is locked in them, as in the Prompt Engineer's Workbench's Architecture tab.

    .. code-block:: python

        detail = resource_detail(request, "Guardrail", "guardrail-rMTAwx")
        detail.model_dump(mode="json")
        # {"kind": "Guardrail", "name": "pii_redaction", "recordLocator": "guardrail-rMTAwx",
        #  "url": "/guardrail/guardrails/rMTAwx/", "manifest": "apiVersion: smarter.sh/v1\\n...",
        #  "manifestError": "", "tree": {...}, "dependents": [{"kind": "LLMClient", ...}]}

    :param request: The request, whose user is authenticated.
    :param kind: The resource's SAM kind, e.g. ``Guardrail``.
    :type kind: str
    :param record_locator: The resource's record locator.
    :type record_locator: str
    :returns: The detail, or None if there is no such resource, the user may not read it, or no broker
        knows its kind.
    :rtype: Optional[ResourceDetail]
    """
    broker_class = Brokers.get_broker(kind)
    instance = readable_instance(request.user, record_locator)
    if broker_class is None or instance is None:
        logger.debug("%s.resource_detail() no %s %s for %s", logger_prefix, kind, record_locator, request.user)
        return None
    name = getattr(instance, "name", None)
    broker = broker_class(request, name=name, kind=kind)
    instance = instance_of_kind(broker, kind, instance)
    if instance is None:
        logger.warning("%s.resource_detail() %s is not a %s", logger_prefix, record_locator, kind)
        return None
    record_locator = getattr(instance, "record_locator", record_locator)
    tree = broker.dependency_tree_node(kind, instance, ancestors=frozenset())
    dependents: list[SAMDependencyTreeNode] = []
    for dependent_kind, rows in broker_class.dependents(instance):
        unique = {row.pk: row for row in rows}
        dependents += [
            broker.dependency_tree_node(
                dependent_kind or str(getattr(row.kind, "value", row.kind)),  # type: ignore[attr-defined]
                row,
                ancestors=frozenset(),
                recursive=False,
            )
            for row in unique.values()
        ]
    manifest, manifest_error = manifest_yaml(kind, instance)
    return ResourceDetail(
        kind=kind,
        name=name,
        record_locator=record_locator,
        url=console_url(record_locator),
        manifest=manifest,
        manifest_error=manifest_error,
        tree=tree,
        dependents=sorted(dependents, key=lambda node: (node.kind, node.name or "")),
    )
