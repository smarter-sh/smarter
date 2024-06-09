"""Customized Django Admin console classes"""

from django.contrib import admin


class RestrictedModelAdmin(admin.ModelAdmin):
    """
    Customized Django Admin console model class that restricts access to the
    model and prevents adding new instances of the model.
    """

    def has_module_permission(self, request):
        return request.user.is_superuser or request.user.is_staff

    # pylint: disable=W0613
    def has_add_permission(self, request, obj=None):
        return False
