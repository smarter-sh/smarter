# pylint: disable=W0212
"""Admin configuration for the chatbot app."""

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import get_cached_user_profile, get_resolved_user
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
    """ChatBot model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [
        "created_at",
        "updated_at",
        "url",
        "user_profile",
        "name",
        "deployed",
        "mode",
        "ready",
        "dns_verification_status",
        "tls_certificate_issuance_status",
    ]

    def ready(self, obj: ChatBot) -> bool:
        return obj.ready()

    def mode(self, obj: ChatBot) -> str:
        return obj.mode(obj.url)

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)

        return smarter_filter_queryset_for_user(user=user, qs=qs)


class ChatBotRequestsAdmin(SmarterCustomerModelAdmin):
    """
    ChatBotRequests model admin.
    """

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
    """ChatBotCustomDomain model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatBotCustomDomain._meta.fields]

    def get_queryset(self, request):
        """
        anyone can see the custom domains since they're controlled at the
        platform level and don't contain sensitive information.
        """
        qs = super().get_queryset(request)
        return qs


class ChatBotCustomDomainDNSAdmin(SmarterCustomerModelAdmin):
    """ChatBotCustomDomainDNS model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatBotCustomDomainDNS._meta.fields]

    def get_queryset(self, request):
        """
        anyone can see the custom domains since they're controlled at the
        platform level and don't contain sensitive information.
        """
        qs = super().get_queryset(request)
        return qs


class ChatBotAPIKeyAdmin(SmarterCustomerModelAdmin):
    """ChatBotAPIKey model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatBotAPIKey._meta.fields]

    def get_queryset(self, request):
        """
        anyone can see the custom domains since they're controlled at the
        platform level and don't contain sensitive information.
        """
        qs = super().get_queryset(request)
        return qs


class ChatBotPluginAdmin(SmarterCustomerModelAdmin):
    """ChatBotPlugin model admin."""

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
    """ChatBotFunctions model admin."""

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


# ChatBot
smarter_restricted_admin_site.register(ChatBot, ChatBotAdmin)
smarter_restricted_admin_site.register(ChatBotCustomDomain, ChatBotCustomDomainAdmin)
smarter_restricted_admin_site.register(ChatBotCustomDomainDNS, ChatBotCustomDomainDNSAdmin)
smarter_restricted_admin_site.register(ChatBotAPIKey, ChatBotAPIKeyAdmin)
smarter_restricted_admin_site.register(ChatBotPlugin, ChatBotPluginAdmin)
smarter_restricted_admin_site.register(ChatBotFunctions, ChatBotFunctionsAdmin)
smarter_restricted_admin_site.register(ChatBotRequests, ChatBotRequestsAdmin)
