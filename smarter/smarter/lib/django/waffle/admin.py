from waffle.admin import SwitchAdmin


class SmarterSwitchAdmin(SwitchAdmin):
    """
    Customized Django Admin console for managing Waffle switches.
    This class restricts access to the module to superusers only.
    """

    ordering = ("name",)

    def has_module_permission(self, request):
        return hasattr(request, "user") and hasattr(request.user, "is_superuser") and request.user.is_superuser  # type: ignore[return-value]
