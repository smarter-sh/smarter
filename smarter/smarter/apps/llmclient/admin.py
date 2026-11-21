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
    search_fields = ("name", "description", "provider", "default_model", "user_profile__user__username")

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
    search_fields = ("llmclient__name", "session_key")

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in LLMClientRequests._meta.fields]

    date_hierarchy = "created_at"

    def get_queryset(self, request):
        """
        Return the requests to the LLMClients that the requesting user has ownership permission for.

        :param request: The admin request.
        :returns: The permitted requests, or an empty queryset if the user does not resolve to a ``User``.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        return qs.filter(llmclient__in=LLMClient.objects.with_ownership_permission_for(user=user))


class LLMClientCustomDomainAdmin(SmarterCustomerModelAdmin):
    """
    LLMClientCustomDomain model admin.

    A CustomDomain is owned, so :class:`~smarter.apps.dashboard.admin.SmarterCustomerModelAdmin` shows staff
    those of their own account. Deleting one goes through its broker, which refuses while an LLMClient uses it.
    """

    model = LLMClientCustomDomain
    search_fields = ("name", "domain_name", "aws_hosted_zone_id", "user_profile__user__username")

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in LLMClientCustomDomain._meta.fields]


class LLMClientCustomDomainDNSAdmin(SmarterCustomerModelAdmin):
    """
    LLMClientCustomDomainDNS model admin, read-only.

    Each row records a DNS record of a CustomDomain's hosted zone, which the platform writes when it registers
    the domain. Adding, changing or deleting a row here would not change the record in DNS, so the rows are
    read-only. Visibility is determined by ownership of the CustomDomain, and role.
    """

    model = LLMClientCustomDomainDNS
    search_fields = ("record_name", "record_value", "custom_domain__domain_name")

    list_display = [field.name for field in LLMClientCustomDomainDNS._meta.fields]
    readonly_fields = [field.name for field in LLMClientCustomDomainDNS._meta.fields]

    def get_queryset(self, request):
        """
        Return the DNS records of the CustomDomains that the requesting user has ownership permission for.

        :param request: The admin request.
        :returns: The permitted rows, or an empty queryset if the user does not resolve to a ``User``.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        custom_domains = LLMClientCustomDomain.objects.with_ownership_permission_for(user=user)
        return qs.filter(custom_domain__in=custom_domains)

    def has_add_permission(self, request, obj=None) -> bool:
        """
        Never add a DNS record in the admin: the platform writes them, and DNS wouldn't change.

        :param request: The admin request.
        :param obj: Unused.
        :returns: False.
        """
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        """
        Never change a DNS record in the admin: DNS wouldn't change.

        :param request: The admin request.
        :param obj: The row, or None.
        :returns: False.
        """
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        """
        Never delete a DNS record in the admin: the record would stay in DNS, with no row to track it.

        :param request: The admin request.
        :param obj: The row, or None.
        :returns: False.
        """
        return False


class LLMClientAPIKeyAdmin(SmarterCustomerModelAdmin):
    """LLMClientAPIKey model admin."""

    model = LLMClientAPIKey
    search_fields = ("llmclient__name", "api_key__name")

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in LLMClientAPIKey._meta.fields]

    def get_queryset(self, request):
        """
        Return the api keys of the LLMClients that the requesting user has ownership permission for.

        :param request: The admin request.
        :returns: The permitted rows, or an empty queryset if the user does not resolve to a ``User``.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        return qs.filter(llmclient__in=LLMClient.objects.with_ownership_permission_for(user=user))


class LLMClientPluginAdmin(SmarterCustomerModelAdmin):
    """
    LLMClientPlugin model admin.

    Descends from LLMClient, so visibility is
    determined by the parent LLMClient and role.
    """

    model = LLMClientPlugin
    search_fields = ("llmclient__name", "plugin_meta__name")

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
    search_fields = ("llmclient__name", "extension__slug", "extension__display_name")

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
    search_fields = ("llmclient__name", "mcpclient__name")

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
