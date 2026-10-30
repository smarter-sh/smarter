"""Django admin of Smarter annotations."""

from smarter.apps.dashboard.admin import (
    SmarterStaffOnlyModelAdmin,
    smarter_restricted_admin_site,
)

from .models import Annotation


class AnnotationAdmin(SmarterStaffOnlyModelAdmin):
    """Annotations, searchable by key and value."""

    list_display = ("key", "value", "content_type", "object_id", "updated_at")
    list_filter = ("content_type", "prefix")
    search_fields = ("key", "value")
    readonly_fields = ("prefix", "created_at", "updated_at")


smarter_restricted_admin_site.register(Annotation, AnnotationAdmin)
