# pylint: disable=C0115,W0212
"""Account admin."""

import logging

from django import forms

# from django.contrib import admin
from django.http.request import HttpRequest
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from smarter.apps.account.models import User, UserProfile, get_resolved_user
from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    smarter_restricted_admin_site,
)
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.mixins import SmarterHelperMixin

from .models import Secret

logger = logging.getLogger(__name__)


class SecretAdminForm(forms.ModelForm):
    """Custom form for SecretAdmin to handle the transient 'value' field."""

    value = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=True),
        help_text="Put your secret here...",
    )

    model = Secret
    list_display = ["name", "user_profile", "description", "expires_at", "value"]
    logger_prefix = formatted_text(f"{__name__}.SecretAdminForm()")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)  # Expecting the user to be passed in via kwargs
        logger.debug("%s Initializing SecretAdminForm with args: %s and kwargs: %s", self.logger_prefix, args, kwargs)
        super().__init__(*args, **kwargs)
        if not self.user or not isinstance(self.user, User) or not self.user.is_authenticated:
            logger.error(
                "%s SecretAdminForm initialized without an authenticated user. All fields will be read-only.",
                self.logger_prefix,
            )
            for field in self.fields.values():
                field.disabled = True
            return

        def has_all_permission():
            return False

        if self.instance and self.instance.pk:
            logger.debug("%s Initializing SecretAdminForm for existing Secret: %s", self.logger_prefix, self.instance)
            try:
                if has_all_permission():
                    instance: Secret = self.instance
                    self.fields["value"].initial = instance.get_secret(update_last_accessed=False)
                else:
                    logger.debug(
                        "%s User %s does not have permission to view the Secret value. Setting 'value' field to '********'.",
                        self.logger_prefix,
                        self.user,
                    )
                    self.fields["value"].initial = "********"
            # pylint: disable=broad-except
            except Exception as e:
                logger.exception(
                    "%s Failed to initialize 'value' field for Secret with id %s. Got the following error: %s",
                    self.logger_prefix,
                    self.instance.pk,
                    e,
                )
                self.fields["value"].initial = None

    def clean(self):
        """Ensure the transient 'value' field is included in cleaned_data."""
        cleaned_data = super().clean()
        if not cleaned_data or "value" not in cleaned_data:
            raise forms.ValidationError("The 'value' field is required.")
        return cleaned_data

    def clean_value(self):
        value = self.cleaned_data.get("value")
        if value and not isinstance(value, str):
            raise forms.ValidationError("The value must be a string.")
        return value


# @admin.register(Secret)
class SecretAdmin(SmarterCustomerModelAdmin, SmarterHelperMixin):
    """
    Secret model admin. This is a primary Smarter resource, that descends
    directly from MetaDataWithOwnershipModel. Visibility of Secrets is
    determined by ownership and role.
    """

    logger_prefix = formatted_text(f"{__name__}.SecretAdmin()")
    request: HttpRequest
    user: User
    user_profile: UserProfile

    model = Secret

    form = SecretAdminForm
    readonly_fields = (
        "created_at",
        "updated_at",
        "last_accessed",
        "display_value",
    )
    fields = (
        "name",
        "user_profile",
        "description",
        "expires_at",
        "display_value",
    )
    list_display = ("user_profile", "name", "description", "created_at", "updated_at", "last_accessed", "expires_at")

    def changelist_view(self, request, extra_context=None):
        self.request = request
        return super().changelist_view(request, extra_context=extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        self.request = request
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def display_value(self, obj: Secret):
        """
        Display the secret value as '********' for users who do not have
        permission to view it.
        """

        def has_all_permission() -> bool:
            """
            Determine if the current user has permission to view the Secret value.
             - Superusers can view all secrets.
             - The owner of the secret can view it.
             - All other users cannot view the secret value.
            """
            if Secret.objects.filter(pk=obj.pk).with_ownership_permission_for(user=self.user).exists():
                return True
            return False

        logger.debug("%s.display_value() called for Secret: %s", self.logger_prefix, str(obj))
        if not isinstance(obj, Secret):
            logger.error(
                "%s.display_value() called with an object that is not a Secret instance: %s",
                self.logger_prefix,
                obj,
            )
            return "********"

        if not hasattr(self.request, "user"):
            logger.error(
                "%s.display_value() called without a request user. Cannot determine permissions to display Secret value.",
                self.logger_prefix,
            )
            return "********"

        self.user = self.request.user  # type: ignore
        self.user_profile = UserProfile.get_cached_object(user=self.user)  # type: ignore
        retval = obj.get_secret(update_last_accessed=False)
        logger.debug(
            "%s.display_value() Retrieved secret value for Secret %s. Checking permissions for user %s. Actual value: %s",
            self.logger_prefix,
            str(obj),
            self.user,
            self.mask_string(retval),
        )

        if has_all_permission():
            logger.debug(
                "%s.display_value() User %s has permission to view the Secret value. Displaying actual value.",
                self.logger_prefix,
                self.user,
            )
            return retval

        logger.debug(
            "%s.display_value() User %s does not have permission to view the Secret value. Displaying masked value.",
            self.logger_prefix,
            self.user,
        )

        return self.mask_string(retval)

    display_value.short_description = "Value"

    def get_form(self, request, obj=None, change=False, **kwargs):
        # Get the base form class
        form = super().get_form(request, obj, change=change, **kwargs)

        # Create a dynamic subclass to inject the request/user at initialization
        class CustomForm(form):
            def __init__(self, *args, **kwargs):
                # Inject custom kwargs here
                kwargs["user"] = request.user
                super().__init__(*args, **kwargs)

        return CustomForm

    def save_model(self, request: HttpRequest, obj: Secret, form: SecretAdminForm, change):
        value = form.cleaned_data.get("value")
        if value:
            obj.encrypted_value = Secret.encrypt(value=value)
        super().save_model(request, obj, form, change)

    def get_queryset(self, request: HttpRequest):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        return Secret.objects.with_ownership_permission_for(user=user).filter(id__in=qs)


class CustomPasswordWidget(forms.Widget):
    """Custom widget for the password field in the UserChangeForm."""

    def render(self, name, value, attrs=None, renderer=None):
        """
        use a placeholder and let the admin render the anchor correctly
        This works because the admin will replace __pk__ with the actual user id
        """
        url = "../password/"  # relative to the change page, works in Django admin
        return mark_safe(f'<a href="{url}" style="color: blue;">CHANGE PASSWORD</a>')  # nosec


smarter_restricted_admin_site.register(Secret, SecretAdmin)
