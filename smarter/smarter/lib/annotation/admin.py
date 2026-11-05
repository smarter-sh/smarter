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

    def get_readonly_fields(self, request, obj=None):
        """
        Keep an annotation on its resource once it exists.

        Saving a row makes the cached annotations of the resource that it points at stale. Moving
        the row to another resource would leave the first resource's cached annotations unchanged.

        :param request: The admin request.
        :param obj: The annotation being edited, or None when one is being added.
        :returns: The read-only fields, plus ``content_type`` and ``object_id`` for an existing annotation.
        """
        readonly = tuple(super().get_readonly_fields(request, obj))
        if obj is not None:
            readonly += ("content_type", "object_id")
        return readonly


smarter_restricted_admin_site.register(Annotation, AnnotationAdmin)
