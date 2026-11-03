# pylint: disable=W0212
"""Admin configuration for the llmclient app."""

from smarter.apps.account.models import User, get_resolved_user
from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    smarter_restricted_admin_site,
)
from smarter.lib import logging

from .models import (
    LLMClient,
    LLMClientAPIKey,
    LLMClientCustomDomain,
    LLMClientCustomDomainDNS,
    LLMClientExtensions,
    LLMClientMCPClients,
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
        """
        Show whether the LLMClient is ready to serve prompts.

        :param obj: The LLMClient in the changelist row.
        :returns: The LLMClient's ``ready`` property.
        """
        return obj.ready

    def mode(self, obj: LLMClient) -> str:
        """
        Show the mode the LLMClient runs in at its own url.

        :param obj: The LLMClient in the changelist row.
        :returns: The mode that ``LLMClient.mode()`` returns for the LLMClient's ``url``.
        """
        return obj.mode(obj.url)

    def get_queryset(self, request):
        """
        Return the LLMClients the requesting user has ownership permission for.

        :param request: The admin request.
        :returns: The permitted LLMClients, or an empty queryset if the user does not resolve to a ``User``.
        """
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
        """
        Return the LLMClients the requesting user has ownership permission for, limited to the admin's queryset.

        :param request: The admin request.
        :returns: The permitted LLMClients whose ids match a primary key in the default
            ``LLMClientRequests`` queryset, or an empty queryset if the user does not resolve to a ``User``.
        """
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
        """
        Return the LLMClient plugins whose LLMClient the requesting user has ownership permission for.

        :param request: The admin request.
        :returns: The permitted rows, or an empty queryset if the user does not resolve to a ``User``.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()

        return qs.filter(llmclient__in=LLMClient.objects.with_ownership_permission_for(user=user))


class LLMClientExtensionsAdmin(SmarterCustomerModelAdmin):
    """
    LLMClientExtensions model admin.

    Visibility is determined by ownership of the parent LLMClient, and role.
    """

    model = LLMClientExtensions

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ["llmclient", "extension", "created_at", "updated_at"]

    def get_queryset(self, request):
        """
        Return the LLMClient extensions whose LLMClient the requesting user has ownership permission for.

        :param request: The admin request.
        :returns: The permitted rows, or an empty queryset if the user does not resolve to a ``User``.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        return qs.filter(llmclient__in=LLMClient.objects.with_ownership_permission_for(user=user))


class LLMClientMCPClientsAdmin(SmarterCustomerModelAdmin):
    """
    LLMClientMCPClients model admin.

    Visibility is determined by ownership of the parent LLMClient, and role.
    """

    model = LLMClientMCPClients

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ["llmclient", "mcpclient", "created_at", "updated_at"]

    def get_queryset(self, request):
        """
        Return the LLMClient MCP clients whose LLMClient the requesting user has ownership permission for.

        :param request: The admin request.
        :returns: The permitted rows, or an empty queryset if the user does not resolve to a ``User``.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        return qs.filter(llmclient__in=LLMClient.objects.with_ownership_permission_for(user=user))


smarter_restricted_admin_site.register(LLMClient, LLMClientAdmin)
smarter_restricted_admin_site.register(LLMClientCustomDomain, LLMClientCustomDomainAdmin)
smarter_restricted_admin_site.register(LLMClientCustomDomainDNS, LLMClientCustomDomainDNSAdmin)
smarter_restricted_admin_site.register(LLMClientAPIKey, LLMClientAPIKeyAdmin)
smarter_restricted_admin_site.register(LLMClientPlugin, LLMClientPluginAdmin)
smarter_restricted_admin_site.register(LLMClientExtensions, LLMClientExtensionsAdmin)
smarter_restricted_admin_site.register(LLMClientMCPClients, LLMClientMCPClientsAdmin)
smarter_restricted_admin_site.register(LLMClientRequests, LLMClientRequestsAdmin)
