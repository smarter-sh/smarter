# pylint: disable=W0212
"""Admin configuration for the llm_client app."""

import logging

from smarter.apps.account.models import User, get_resolved_user
from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    smarter_restricted_admin_site,
)

from .models import (
    LLMClient,
    LLMClientAPIKey,
    LLMClientCustomDomain,
    LLMClientCustomDomainDNS,
    LLMClientFunctions,
    LLMClientPlugin,
    LLMClientRequests,
)

logger = logging.getLogger(__name__)


class LLMClientAdmin(SmarterCustomerModelAdmin):
    """
    LLMClient model admin.

    This is a primary
    Smarter resource, that descends directly from MetaDataWithOwnershipModel.
    Visibility of LLMClients is determined by ownership and role.
    """

    model = LLMClient

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [
        "name",
        "user_profile",
        "url",
        "deployed",
        "mode",
        "ready",
        "dns_verification_status",
        "tls_certificate_issuance_status",
        "created_at",
        "updated_at",
    ]
    ordering = ["-updated_at"]

    def ready(self, obj: LLMClient) -> bool:
        return obj.ready

    def mode(self, obj: LLMClient) -> str:
        return obj.mode(obj.url)

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        return LLMClient.objects.with_ownership_permission_for(user=user)


class LLMClientRequestsAdmin(SmarterCustomerModelAdmin):
    """
    LLMClientRequests model admin.

    Descends from LLMClient, so visibility is
    determined by the parent LLMClient ownership and role.
    """

    model = LLMClientRequests

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in LLMClientRequests._meta.fields]

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        return LLMClient.objects.with_ownership_permission_for(user=user).filter(id__in=qs)


class LLMClientCustomDomainAdmin(SmarterCustomerModelAdmin):
    """
    LLMClientCustomDomain model admin.

    This is a resource that is managed at the
    platform level and doesn't contain sensitive information,
    so we allow all users to see it regardless of ownership.
    """

    model = LLMClientCustomDomain

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in LLMClientCustomDomain._meta.fields]

    def get_queryset(self, request):
        """Visible to any authenticated user."""
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        if user.is_authenticated:
            return qs
        else:
            return qs.none()


class LLMClientCustomDomainDNSAdmin(SmarterCustomerModelAdmin):
    """LLMClientCustomDomainDNS model admin."""

    model = LLMClientCustomDomainDNS

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in LLMClientCustomDomainDNS._meta.fields]

    def get_queryset(self, request):
        """Visible to any authenticated user."""
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()

        if user.is_authenticated:
            return qs
        else:
            return qs.none()


class LLMClientAPIKeyAdmin(SmarterCustomerModelAdmin):
    """LLMClientAPIKey model admin."""

    model = LLMClientAPIKey

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in LLMClientAPIKey._meta.fields]

    def get_queryset(self, request):
        """Visible to any authenticated user."""
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        if user.is_authenticated:
            return qs
        else:
            return qs.none()


class LLMClientPluginAdmin(SmarterCustomerModelAdmin):
    """
    LLMClientPlugin model admin.

    Descends from LLMClient, so visibility is
    determined by the parent LLMClient and role.
    """

    model = LLMClientPlugin

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in LLMClientPlugin._meta.fields]

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()

        llm_clients = LLMClient.objects.with_ownership_permission_for(user=user).filter(id__in=qs)
        return LLMClientPlugin.objects.filter(llm_client__in=llm_clients)


class LLMClientFunctionsAdmin(SmarterCustomerModelAdmin):
    """
    LLMClientFunctions model admin.

    Descends from LLMClientPlugin, so visibility is
    determined by the parent LLMClientPlugin and role.
    """

    model = LLMClientFunctions

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in LLMClientFunctions._meta.fields]

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()

        llm_clients = LLMClient.objects.with_ownership_permission_for(user=user).filter(id__in=qs)
        return LLMClientFunctions.objects.filter(llm_client__in=llm_clients)


smarter_restricted_admin_site.register(LLMClient, LLMClientAdmin)
smarter_restricted_admin_site.register(LLMClientCustomDomain, LLMClientCustomDomainAdmin)
smarter_restricted_admin_site.register(LLMClientCustomDomainDNS, LLMClientCustomDomainDNSAdmin)
smarter_restricted_admin_site.register(LLMClientAPIKey, LLMClientAPIKeyAdmin)
smarter_restricted_admin_site.register(LLMClientPlugin, LLMClientPluginAdmin)
smarter_restricted_admin_site.register(LLMClientFunctions, LLMClientFunctionsAdmin)
smarter_restricted_admin_site.register(LLMClientRequests, LLMClientRequestsAdmin)
