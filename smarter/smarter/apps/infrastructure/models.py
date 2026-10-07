"""
Models of the infrastructure app.

:class:`InfrastructureResource` is the ledger of the cloud resources that the platform creates:
DNS zones and records, TLS certificates, and billable Kubernetes resources, whichever cloud
provider created them. The receivers of the infrastructure signals keep it, see
:mod:`smarter.apps.infrastructure.receivers`, so that what the platform has provisioned, and
what it costs, can be audited without asking each cloud.
"""

from typing import Optional

from django.db import models
from django.utils import timezone

from smarter.lib.django.models import TimestampedModel


class InfrastructureResource(TimestampedModel):
    """A cloud resource that the platform created, and whether it still exists."""

    class Status(models.TextChoices):
        """Whether the resource exists."""

        ACTIVE = "active", "Active"
        DESTROYED = "destroyed", "Destroyed"

    provider = models.CharField(max_length=32, help_text="The cloud provider, e.g. aws.")
    service = models.CharField(max_length=32, help_text="The infrastructure service, e.g. dns.")
    resource_type = models.CharField(max_length=64, help_text="The kind of resource, e.g. dns.zone.")
    resource_name = models.CharField(max_length=255, help_text="The resource's name, e.g. example.com.")
    resource_id = models.CharField(
        max_length=512, blank=True, default="", help_text="The provider's id of the resource, if any."
    )
    billable = models.BooleanField(default=False, help_text="Whether the provider bills for the resource.")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    destroyed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Infrastructure Resource"
        verbose_name_plural = "Infrastructure Resources"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider", "resource_type", "resource_name"]),
            models.Index(fields=["status", "billable"]),
        ]

    def __str__(self) -> str:
        return f"{self.provider} {self.resource_type} {self.resource_name} ({self.status})"

    # pylint: disable=too-many-arguments
    @classmethod
    def record_created(
        cls,
        provider: str,
        service: str,
        resource_type: str,
        resource_name: str,
        resource_id: Optional[str] = None,
        billable: bool = False,
    ) -> "InfrastructureResource":
        """
        Record that a resource was created, or updated.

        A resource that is already active is updated, rather than recorded twice.
        """
        resource = cls.objects.filter(
            provider=provider, resource_type=resource_type, resource_name=resource_name, status=cls.Status.ACTIVE
        ).first()
        if resource is None:
            return cls.objects.create(
                provider=provider,
                service=service,
                resource_type=resource_type,
                resource_name=resource_name,
                resource_id=resource_id or "",
                billable=billable,
            )
        resource.resource_id = resource_id or resource.resource_id
        resource.billable = billable
        resource.save(update_fields=["resource_id", "billable", "updated_at"])
        return resource

    # pylint: disable=too-many-arguments
    @classmethod
    def record_destroyed(
        cls,
        provider: str,
        service: str,
        resource_type: str,
        resource_name: str,
        resource_id: Optional[str] = None,
        billable: bool = False,
    ) -> "InfrastructureResource":
        """
        Record that a resource was destroyed.

        A resource that the ledger does not know, e.g. one created before it existed, is
        recorded as destroyed.
        """
        now = timezone.now()
        resource = cls.objects.filter(
            provider=provider, resource_type=resource_type, resource_name=resource_name, status=cls.Status.ACTIVE
        ).first()
        if resource is None:
            return cls.objects.create(
                provider=provider,
                service=service,
                resource_type=resource_type,
                resource_name=resource_name,
                resource_id=resource_id or "",
                billable=billable,
                status=cls.Status.DESTROYED,
                destroyed_at=now,
            )
        resource.status = cls.Status.DESTROYED
        resource.destroyed_at = now
        resource.save(update_fields=["status", "destroyed_at", "updated_at"])
        return resource


__all__ = ["InfrastructureResource"]
