"""Admin configuration for the vectorstore app."""

from django.contrib import admin

from smarter.apps.account.models import User, get_resolved_user
from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    smarter_restricted_admin_site,
)

from .models import VectorstoreDocument, VectorstoreMeta, VectorstoreSnapshot


class VectorstoreDocumentInline(admin.TabularInline):
    """A vectorstore's documents, without their content."""

    model = VectorstoreDocument
    extra = 0
    fields = ("name", "source", "content_type", "status", "chunk_count", "loaded_at", "status_message")
    readonly_fields = fields
    can_delete = False
    show_change_link = False


class VectorstoreSnapshotInline(admin.TabularInline):
    """A vectorstore's snapshots, or backups."""

    model = VectorstoreSnapshot
    extra = 0
    fields = ("name", "status", "size_bytes", "vector_count", "scheduled", "created_at")
    readonly_fields = fields
    can_delete = False


class VectorstoreAdmin(SmarterCustomerModelAdmin):
    """
    VectorstoreMeta model admin.

    Vectorstores are created with manifests, so state is read only here.

    Visibility of Vectorstores is determined by ownership and role.
    """

    model = VectorstoreMeta
    inlines = [VectorstoreDocumentInline, VectorstoreSnapshotInline]
    readonly_fields = (
        "created_at",
        "updated_at",
        "spec",
        "status",
        "status_message",
        "index_name",
        "endpoint_url",
        "api_key_secret",
        "vector_count",
        "stats",
        "deployed_at",
        "last_checked_at",
        "last_snapshot_at",
        "last_maintenance_at",
    )
    list_display = [
        "name",
        "user_profile",
        "backend",
        "hosting",
        "status",
        "vector_count",
        "embeddings_provider",
        "embeddings_model",
        "updated_at",
    ]
    list_filter = ("backend", "hosting", "status")
    ordering = ["-updated_at"]

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        return VectorstoreMeta.objects.with_ownership_permission_for(user=user).filter(id__in=qs)


smarter_restricted_admin_site.register(VectorstoreMeta, VectorstoreAdmin)
