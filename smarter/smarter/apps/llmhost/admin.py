# pylint: disable=W0212
"""Admin configuration for the llmhost app."""

from django.contrib import admin, messages

from smarter.apps.account.models import User, get_resolved_user
from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    smarter_restricted_admin_site,
)
from smarter.lib import logging

from .models import LLMHost, LLMHostCompute, LLMHostEvent
from .services.compute import ComputeProvisioner
from .services.exceptions import LLMHostComputeError

logger = logging.getLogger(__name__)


class LLMHostAdmin(SmarterCustomerModelAdmin):
    """
    LLMHost model admin.

    This is a primary Smarter resource, that descends directly from
    MetaDataWithOwnershipModel. Visibility of LLMHosts is determined by ownership and role.
    LLMHosts are configured with manifests, and launched with ``smarter deploy``, so the
    observed state is read only.
    """

    model = LLMHost

    readonly_fields = (
        "created_at",
        "updated_at",
        "status",
        "status_message",
        "ready_replicas",
        "endpoint_url",
        "public_url",
        "health_check_url",
        "last_health_check_at",
        "last_health_ok",
        "deployed_at",
    )
    list_display = [
        "name",
        "user_profile",
        "model_repository",
        "inference_engine",
        "compute",
        "gpu_count",
        "replicas",
        "status",
        "updated_at",
    ]
    list_filter = ["status", "inference_engine", "model_source", "model_task"]
    search_fields = ["name", "model_repository", "description"]
    ordering = ["-updated_at"]

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        return LLMHost.objects.with_ownership_permission_for(user=user)


class LLMHostEventAdmin(SmarterCustomerModelAdmin):
    """LLMHostEvent model admin: the lifecycle of LLMHosts.

    Read only.
    """

    model = LLMHostEvent

    list_display = ["created_at", "llmhost_name", "event_type", "status", "message"]
    list_filter = ["event_type", "status"]
    search_fields = ["llmhost_name", "message"]
    ordering = ["-created_at"]

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in LLMHostEvent._meta.fields]

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        """Visibility is determined by ownership of the LLMHost, and role."""
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        llmhosts = LLMHost.objects.with_ownership_permission_for(user=user).values("id")
        return qs.filter(llmhost__in=llmhosts)


class LLMHostComputeAdmin(SmarterCustomerModelAdmin):
    """
    LLMHostCompute model admin: the kinds of node, and node groups, that LLMHosts run on.

    LLMHostComputes are configured with manifests, so the node group's observed state is read
    only. Visibility is determined by ownership and role: the built-in ones are owned by the
    Smarter admin.
    """

    model = LLMHostCompute

    readonly_fields = (
        "created_at",
        "updated_at",
        "nodegroup_status",
        "desired_nodes",
        "ready_nodes",
        "status_message",
        "last_reconciled_at",
    )
    list_display = [
        "name",
        "user_profile",
        "instance_type",
        "gpu_type",
        "gpu_count",
        "price_per_hour",
        "nodegroup_status",
        "ready_nodes",
        "desired_nodes",
        "max_nodes",
    ]
    list_filter = ["gpu_type", "nodegroup_status"]
    search_fields = ["name", "instance_type", "description"]
    ordering = ["name"]
    actions = ["reconcile"]

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        return LLMHostCompute.objects.with_ownership_permission_for(user=user)

    @admin.action(description="Reconcile the node groups with their LLMHosts")
    def reconcile(self, request, queryset):
        provisioner = ComputeProvisioner()
        for compute in queryset:
            try:
                state = provisioner.reconcile(compute)
                self.message_user(request, f"{compute}: {'; '.join(state.actions) or state.message}")
            except LLMHostComputeError as e:
                self.message_user(request, f"{compute}: {e}", level=messages.ERROR)


smarter_restricted_admin_site.register(LLMHost, LLMHostAdmin)
smarter_restricted_admin_site.register(LLMHostCompute, LLMHostComputeAdmin)
smarter_restricted_admin_site.register(LLMHostEvent, LLMHostEventAdmin)
