# pylint: disable=W0212
"""Admin configuration for the chatbot app."""

from smarter.apps.account.models import get_resolved_user
from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    smarter_filter_queryset_for_user,
    smarter_restricted_admin_site,
)

from .models import (
    ChatBot,
    ChatBotAPIKey,
    ChatBotCustomDomain,
    ChatBotCustomDomainDNS,
    ChatBotFunctions,
    ChatBotPlugin,
    ChatBotRequests,
)


class ChatBotAdmin(SmarterCustomerModelAdmin):
    """
    ChatBot model admin. This is a primary
    Smarter resource, that descends directly from MetaDataWithOwnershipModel.
    Visibility of ChatBots is determined by ownership and role.
    """

    model = ChatBot

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

    def ready(self, obj: ChatBot) -> bool:
        return obj.ready

    def mode(self, obj: ChatBot) -> str:
        return obj.mode(obj.url)

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)

        return smarter_filter_queryset_for_user(user=user, qs=qs)


class ChatBotRequestsAdmin(SmarterCustomerModelAdmin):
    """
    ChatBotRequests model admin. Descends from ChatBot, so visibility is
    determined by the parent ChatBot ownership and role.
    """

    model = ChatBotRequests

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatBotRequests._meta.fields]

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)

        return smarter_filter_queryset_for_user(
            user=user,
            qs=qs,
            account_filter="chatbot__user_profile__account",
            user_profile_filter="chatbot__user_profile",
        )


class ChatBotCustomDomainAdmin(SmarterCustomerModelAdmin):
    """
    ChatBotCustomDomain model admin. This is a resource that is managed at the
    platform level and doesn't contain sensitive information,
    so we allow all users to see it regardless of ownership.
    """

    model = ChatBotCustomDomain

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatBotCustomDomain._meta.fields]

    def get_queryset(self, request):
        """
        visible to any authenticated user.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if user.is_authenticated:
            return qs
        else:
            return qs.none()


class ChatBotCustomDomainDNSAdmin(SmarterCustomerModelAdmin):
    """ChatBotCustomDomainDNS model admin."""

    model = ChatBotCustomDomainDNS

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatBotCustomDomainDNS._meta.fields]

    def get_queryset(self, request):
        """
        visible to any authenticated user.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if user.is_authenticated:
            return qs
        else:
            return qs.none()


class ChatBotAPIKeyAdmin(SmarterCustomerModelAdmin):
    """ChatBotAPIKey model admin."""

    model = ChatBotAPIKey

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatBotAPIKey._meta.fields]

    def get_queryset(self, request):
        """
        visible to any authenticated user.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if user.is_authenticated:
            return qs
        else:
            return qs.none()


class ChatBotPluginAdmin(SmarterCustomerModelAdmin):
    """
    ChatBotPlugin model admin. Descends from ChatBot, so visibility is
    determined by the parent ChatBot and role.
    """

    model = ChatBotPlugin

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatBotPlugin._meta.fields]

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)

        return smarter_filter_queryset_for_user(
            user=user,
            qs=qs,
            account_filter="chatbot__user_profile__account",
            user_profile_filter="chatbot__user_profile",
        )


class ChatBotFunctionsAdmin(SmarterCustomerModelAdmin):
    """
    ChatBotFunctions model admin. Descends from ChatBotPlugin, so visibility is
    determined by the parent ChatBotPlugin and role.
    """

    model = ChatBotFunctions

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatBotFunctions._meta.fields]

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)

        return smarter_filter_queryset_for_user(
            user=user,
            qs=qs,
            account_filter="chatbot__user_profile__account",
            user_profile_filter="chatbot__user_profile",
        )


smarter_restricted_admin_site.register(ChatBot, ChatBotAdmin)
smarter_restricted_admin_site.register(ChatBotCustomDomain, ChatBotCustomDomainAdmin)
smarter_restricted_admin_site.register(ChatBotCustomDomainDNS, ChatBotCustomDomainDNSAdmin)
smarter_restricted_admin_site.register(ChatBotAPIKey, ChatBotAPIKeyAdmin)
smarter_restricted_admin_site.register(ChatBotPlugin, ChatBotPluginAdmin)
smarter_restricted_admin_site.register(ChatBotFunctions, ChatBotFunctionsAdmin)
smarter_restricted_admin_site.register(ChatBotRequests, ChatBotRequestsAdmin)
