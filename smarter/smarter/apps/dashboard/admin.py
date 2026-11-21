# pylint: disable=missing-class-docstring,missing-function-docstring,W0613
"""
Custom Django admin site and model admin classes for the dashboard app.

This module rebuilds the Django admin site with fine-grained, role-based
access control. Instead of using Django's default ``AdminSite``, a
:class:`RestrictedAdminSite` instance is registered. Django lets only active
``is_staff`` users into the site, so it is a tool for the platform's
superusers and for each account's staff. Everyone else uses the web console.
The site enforces these tiers across all registered models:

- **Superuser**: every row of every model, with add, change and delete.
- **Staff (account admin)**: the rows of their own account, of the models
  registered with :class:`SmarterCustomerModelAdmin` or
  :class:`SmarterStaffOnlyModelAdmin`. They may change and delete the rows
  they have ownership permission for, and add none.
- **Anyone else**: no access.

Module-level helpers
--------------------
:func:`smarter_admin_user`
    Returns the request's authenticated ``User``, or None.

:func:`smarter_is_staff`
    Returns ``True`` if the requesting user is a staff member or superuser.

:func:`smarter_has_ud_permission`
    Returns ``True`` if the requesting user may update or delete the given
    object, based on ownership and account association.

:func:`smarter_scoped_queryset`
    Limits a queryset of owned resources to those the user has ownership
    permission for.

Model admin classes
-------------------
:class:`SmarterModelAdminMixin`
    What every Smarter model admin does: deletes a SAM resource with its
    broker, exports SAM resources as manifests, and keeps its lists and forms
    fast on large tables.

:class:`SmarterCustomerModelAdmin`
    Shows staff the rows of their own account; change and delete need
    ownership permission.

:class:`SmarterStaffOnlyModelAdmin`
    The same, and checks that the user is staff at every step.

:class:`SmarterSuperUserOnlyModelAdmin`
    Restricts all operations to superusers only.

:class:`SmarterAutoModelAdmin` and :func:`smarter_auto_model_admin`
    A superuser-only admin whose list, filters and search are built from the
    model's fields, for the models that have no admin of their own.

Admin site
----------
:class:`RestrictedAdminSite`
    Custom :class:`~django.contrib.admin.AdminSite` whose header names the
    current user's role and the version.

:data:`smarter_restricted_admin_site`
    The singleton :class:`RestrictedAdminSite` instance used throughout the
    project (``name="restricted_admin_site"``).

Registered models
-----------------
- :class:`~smarter.apps.dashboard.models.EmailContactList`: registered with
  :class:`EmailContactListAdmin` (superuser-only).
- Django's :class:`~django.contrib.admin.models.LogEntry`, the admin's own
  audit log: registered with :class:`LogEntryAdmin` (superuser-only, read-only).
"""

from typing import Optional

from django.contrib import admin, messages
from django.contrib.admin import widgets
from django.contrib.admin.models import LogEntry
from django.contrib.admin.options import IS_POPUP_VAR
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from smarter.__version__ import __version__
from smarter.apps.account.models import (
    Account,
    MetaDataWithOwnershipModel,
    UserProfile,
    get_resolved_user,
)
from smarter.lib import logging

from .models import EmailContactList

logger = logging.getSmarterLogger(__name__)

SITE_HEADER = "Smarter Admin Console v" + __version__
"""The admin console's header, before the user's role."""

RAW_ID_MODELS: tuple[type[models.Model], ...] = (User, UserProfile, Account)
"""
The related models whose foreign keys a form shows as an id with a lookup, not a dropdown.

Each of these tables grows with the platform's users, and a dropdown would render every row.
"""

DELETE_ERRORS_ATTRIBUTE = "smarter_admin_delete_errors"
"""The request attribute in which :meth:`SmarterModelAdminMixin.delete_model` keeps why a delete failed."""

AUTO_LIST_DISPLAY_LIMIT = 8
"""The most columns that :class:`SmarterAutoModelAdmin` lists."""

OWNED_RESOURCE_SEARCH_FIELDS = ("name", "description", "user_profile__user__username")
"""What the list of an owned resource searches, unless its admin names its own ``search_fields``."""

UNSEARCHABLE_FIELD_NAMES = frozenset(
    ("password", "secret", "token", "salt", "code", "handle", "session_key", "digest", "sha256", "version")
)
"""The text fields that :func:`smarter_auto_model_admin` never searches: credentials, hashes and versions."""

UNSEARCHABLE_FIELD_SUFFIXES = ("_key", "_secret", "_token", "_digest", "_hash")
"""The suffixes of the field names that :func:`smarter_auto_model_admin` never searches."""


def smarter_admin_user(request: HttpRequest) -> Optional[User]:
    """
    Return the request's authenticated user.

    An anonymous visitor, e.g. of the admin's login page, gets None without a warning.

    :param request: The admin request.
    :returns: The resolved ``User``, or None if the request has no authenticated user.
    """
    request_user = getattr(request, "user", None)
    if request_user is None:
        return None
    if not request_user.is_authenticated:
        return None
    user = get_resolved_user(request_user)  # type: ignore
    if not isinstance(user, User):
        logger.warning("Unexpected user type: %s", type(user))
        return None
    return user


def smarter_is_staff(request: HttpRequest) -> bool:
    """
    Helper method to determine if the user is a staff member.

    param request: HttpRequest object containing user information
    rtype: bool
    return: True if the user is a staff member, False otherwise
    """
    user = get_resolved_user(request.user)  # type: ignore
    if not isinstance(user, User):
        return False
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return False


def smarter_has_ud_permission(request: HttpRequest, obj=None) -> bool:
    """
    Helper method to determine if the user has permission to Update or Delete (UD) an object based on ownership and account association.

    param request: HttpRequest object containing user information
    param obj: The object for which update/delete permission is being checked (optional)
    rtype: bool
    return: True if the user has update/delete permission for the object, False otherwise
    """
    # First check if the user is authenticated
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return False
    user = request.user
    if not isinstance(user, User):
        logger.warning("Unexpected user: %s", type(user))
        return False
    if user.is_superuser:
        return True

    if isinstance(obj, (Account, User, UserProfile)):
        return False

    try:
        if isinstance(obj, MetaDataWithOwnershipModel):
            return type(obj).objects.with_ownership_permission_for(user=user).filter(pk=obj.pk).exists()
        return False
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Error checking ownership permission: %s", e)
    return False


def smarter_scoped_queryset(queryset: QuerySet, user: Optional[User]) -> QuerySet:
    """
    Return the rows of a queryset that a user may see in the admin.

    A superuser sees every row. Of a model of owned resources, another user sees those they have ownership
    permission for: a staff user, those of their own account. The rows of any other model are returned as they
    are, and the model's admin scopes them in its own ``get_queryset()``, e.g. by the ownership of a parent
    resource.

    :param queryset: The model admin's queryset.
    :param user: The request's user, or None.
    :returns: The rows the user may see.
    """
    if user is None:
        return queryset.none()
    if user.is_superuser:
        return queryset
    model = queryset.model
    if not issubclass(model, MetaDataWithOwnershipModel):
        return queryset
    permitted = model.objects.with_ownership_permission_for(user=user).values("pk")
    return queryset.filter(pk__in=permitted)


def smarter_admin_account_ids(user: User) -> QuerySet:
    """
    Return the ids of the accounts that a user belongs to, which a staff user administers.

    :param user: The user.
    :returns: The ids of the accounts of the user's profiles, as a subquery.
    """
    return UserProfile.objects.filter(user=user).values("account_id")


def smarter_queryset_contains(queryset: QuerySet, obj) -> bool:
    """
    Return whether an object is a row of a queryset.

    :param queryset: The queryset, e.g. a model admin's.
    :param obj: The object.
    :returns: True if ``obj`` is an instance of the queryset's model whose primary key is in it.
    """
    if not isinstance(obj, queryset.model):
        return False
    pk = getattr(obj, "pk", None)
    if pk is None:
        return False
    return queryset.filter(pk=pk).exists()


def smarter_raw_id_fields(model: type[models.Model]) -> tuple[str, ...]:
    """
    Return the foreign keys of a model that a form should show as an id with a lookup.

    :param model: The model.
    :returns: The names of its foreign keys, one-to-one fields and many-to-many fields to a model in
        :data:`RAW_ID_MODELS`.
    """
    names: list[str] = []
    for field in model._meta.get_fields():  # pylint: disable=protected-access
        if not field.concrete:
            continue
        if not field.is_relation:
            continue
        if field.related_model not in RAW_ID_MODELS:
            continue
        names.append(field.name)
    return tuple(names)


def smarter_resource_kind(obj: models.Model) -> Optional[str]:
    """
    Return the SAM kind of a row that is a SAM resource with a broker.

    :param obj: The row.
    :returns: Its kind, e.g. ``Guardrail``, or None if it isn't a SAM resource, or its kind has no broker.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.api.v1.cli.brokers import Brokers
    from smarter.apps.dashboard.resource_detail import kind_of_instance

    kind = kind_of_instance(obj)
    if not kind:
        return None
    if Brokers.get_broker(kind) is None:
        return None
    return kind


def smarter_admin_role(request: HttpRequest) -> str:
    """
    Return the role of the request's user, for the admin console's header.

    :param request: The admin request.
    :returns: ``guest``, ``unknown``, ``superuser``, ``account admin`` (staff), or
        ``customer - <first name> <last name>``.
    """
    user = get_resolved_user(request.user)  # type: ignore
    if isinstance(user, AnonymousUser):
        return "guest"
    if not getattr(user, "is_authenticated", False):
        return "guest"
    if not isinstance(user, User):
        logger.warning("Unexpected user type: %s", type(user))
        return "unknown"
    if user.is_superuser:
        return "superuser"
    if user.is_staff:
        return "account admin"
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    role = "customer - " + first_name + " " + last_name
    return role


class SmarterModelAdminMixin(admin.ModelAdmin):
    """
    What every Smarter model admin does, whatever its permission tier.

    - **Deletes a SAM resource with its broker**, as ``smarter delete`` does. The delete page lists the
      resources that depend on it as protected, so the admin refuses the delete, as the broker would. A delete
      that the page allows is done by the broker, which invalidates the resource's caches and journals the
      delete. Rows of other models are deleted as Django deletes them.
    - **Exports SAM resources as manifests**: the list's *Export the selected resources as manifests* action
      downloads each one's manifest, as ``smarter describe`` returns it, with a Secret's value redacted.
    - **Searches every list of owned resources**, by name, description and owner, unless its admin names
      its own ``search_fields``.
    - **Keeps its lists and forms fast on large tables**: a list joins the foreign keys that it shows,
      and a form shows a foreign key to a user, user profile or account as an id with a lookup, not a
      dropdown of every row.
    """

    def smarter_raw_id_field_names(self) -> tuple[str, ...]:
        """
        Return the foreign keys that the admin's forms show as an id with a lookup.

        :returns: The admin's own ``raw_id_fields``, or, if it names none, those of :func:`smarter_raw_id_fields`.
        """
        if self.raw_id_fields:
            return tuple(self.raw_id_fields)
        return smarter_raw_id_fields(self.model)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Show a foreign key to a large table as an id with a lookup, not a dropdown of every row.

        :param db_field: The model's foreign key.
        :param request: The admin request.
        :param kwargs: The form field's arguments.
        :returns: The form field.
        """
        if "widget" not in kwargs and db_field.name in self.smarter_raw_id_field_names():
            using = kwargs.get("using")
            kwargs["widget"] = widgets.ForeignKeyRawIdWidget(db_field.remote_field, self.admin_site, using=using)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """
        Show a many-to-many field to a large table as ids with a lookup, not a list of every row.

        :param db_field: The model's many-to-many field.
        :param request: The admin request.
        :param kwargs: The form field's arguments.
        :returns: The form field, or None for a field whose intermediary model the admin doesn't show.
        """
        if "widget" not in kwargs and db_field.name in self.smarter_raw_id_field_names():
            using = kwargs.get("using")
            kwargs["widget"] = widgets.ManyToManyRawIdWidget(db_field.remote_field, self.admin_site, using=using)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def get_list_select_related(self, request: HttpRequest):
        """
        Join the foreign keys that the list shows, unless the admin names its own.

        Django joins only the non-null foreign keys of a list by default. A user profile is shown with its user and
        account, so those are joined too.

        :param request: The admin request.
        :returns: The admin's own ``list_select_related``, or the relations of the list's columns.
        """
        if self.list_select_related:
            return self.list_select_related
        names: list[str] = []
        for name in self.get_list_display(request):
            if not isinstance(name, str):
                continue
            try:
                field = self.model._meta.get_field(name)  # pylint: disable=protected-access
            except FieldDoesNotExist:
                continue
            if not field.concrete:
                continue
            if not (field.many_to_one or field.one_to_one):
                continue
            names.append(name)
            if field.related_model is UserProfile:
                names.append(f"{name}__user")
                names.append(f"{name}__account")
        if not names:
            return False
        return names

    def get_search_fields(self, request: HttpRequest):
        """
        Search an owned resource's name, description and owner, unless the admin names its own ``search_fields``.

        :param request: The admin request.
        :returns: The admin's own ``search_fields``, :data:`OWNED_RESOURCE_SEARCH_FIELDS` for a model of owned
            resources, or none.
        """
        if self.search_fields:
            return self.search_fields
        if issubclass(self.model, MetaDataWithOwnershipModel):
            return OWNED_RESOURCE_SEARCH_FIELDS
        return ()

    def get_actions(self, request: HttpRequest, *args, **kwargs):
        """
        Add the export action to the list of a model whose rows are SAM resources.

        :param request: The admin request.
        :param args: Django's other arguments, if any.
        :param kwargs: Django's other keyword arguments, if any.
        :returns: The admin's actions.
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.dashboard.resource_detail import model_has_kind

        actions = super().get_actions(request, *args, **kwargs)
        # Django offers no actions in a popup, or when the admin turns them off.
        if self.actions is None:
            return actions
        if IS_POPUP_VAR in request.GET:
            return actions
        if not model_has_kind(self.model):
            return actions
        if not self.has_view_permission(request):
            return actions
        actions["export_manifests"] = self.get_action("export_manifests")
        return actions

    @admin.action(description="Export the selected resources as manifests")
    def export_manifests(self, request: HttpRequest, queryset: QuerySet):
        """
        Download the selected resources' manifests: one YAML file, or a zip file of several.

        Each manifest is the one that ``smarter describe`` returns to the resource's owner, at
        ``<account number>/<kind>/<name>.yaml`` in the zip file, as Download My Data writes it. A Secret's
        value is redacted. A resource that has no manifest is reported, and left out.

        :param request: The admin request.
        :param queryset: The selected rows.
        :returns: The file, or None, to show the list again, if no resource had a manifest.
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.account.data_export import (
            ExportResource,
            manifest_file,
            zip_files,
        )

        files = []
        taken: set[str] = set()
        for obj in queryset:
            kind = smarter_resource_kind(obj)
            if kind is None:
                self.message_user(request, f"{obj} has no manifest.", level=messages.WARNING)
                continue
            resource = ExportResource.for_instance(kind, obj)
            exported, error = manifest_file(resource, reader=request.user, taken=taken)  # type: ignore[arg-type]
            if exported is None:
                self.message_user(request, error, level=messages.WARNING)
                continue
            files.append(exported)
        if not files:
            return None
        if len(files) == 1:
            exported = files[0]
            file_name = exported.path.rsplit("/", 1)[-1]
            response = HttpResponse(exported.content, content_type="application/yaml")
            response["Content-Disposition"] = f'attachment; filename="{file_name}"'
            return response
        model_name = slugify(self.model._meta.verbose_name_plural)  # pylint: disable=protected-access
        date = timezone.now().strftime("%Y%m%d")
        folder = f"smarter-{model_name}-{date}"
        content = zip_files(files, folder)
        response = HttpResponse(content, content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{folder}.zip"'
        return response

    def get_deleted_objects(self, objs, request: HttpRequest):
        """
        List what a delete would delete, and, as protected, the resources that depend on a SAM resource.

        Django's delete page refuses a delete that has protected objects, so a resource that others depend on
        can't be deleted in the admin, as ``smarter delete`` refuses it.

        :param objs: The rows to delete.
        :param request: The admin request.
        :returns: Django's deleted objects, model count, permissions needed and protected objects, with each
            dependent added to the protected objects.
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.dashboard.resource_detail import dependent_names

        deleted_objects, model_count, perms_needed, protected = super().get_deleted_objects(objs, request)
        protected = list(protected)
        for obj in objs:
            kind = smarter_resource_kind(obj)
            if kind is None:
                continue
            for name in dependent_names(kind, obj, reader=request.user):
                protected.append(f"{name}, which depends on {kind} {obj}")
        return deleted_objects, model_count, perms_needed, protected

    def delete_model(self, request: HttpRequest, obj) -> None:
        """
        Delete a row: a SAM resource with its broker, any other row as Django does.

        Why a broker didn't delete its resource is kept on the request, for :meth:`response_delete`.

        :param request: The admin request.
        :param obj: The row.
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.dashboard.resource_detail import delete_with_broker

        kind = smarter_resource_kind(obj)
        if kind is None:
            super().delete_model(request, obj)
            return
        error = delete_with_broker(kind, obj, reader=request.user)
        if error:
            setattr(request, DELETE_ERRORS_ATTRIBUTE, [f"{kind} {obj} was not deleted: {error}"])

    def delete_queryset(self, request: HttpRequest, queryset: QuerySet) -> None:
        """
        Delete the rows of the list's delete action: each SAM resource with its broker, the others as Django does.

        A resource that its broker didn't delete is reported.

        :param request: The admin request.
        :param queryset: The selected rows.
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.dashboard.resource_detail import delete_with_broker

        other_pks = []
        for obj in queryset:
            kind = smarter_resource_kind(obj)
            if kind is None:
                other_pks.append(obj.pk)
                continue
            error = delete_with_broker(kind, obj, reader=request.user)
            if error:
                self.message_user(request, f"{kind} {obj} was not deleted: {error}", level=messages.ERROR)
        if other_pks:
            super().delete_queryset(request, queryset.model._default_manager.filter(pk__in=other_pks))

    def response_delete(self, request: HttpRequest, obj_display, obj_id):
        """
        Show the list again after a delete, with why it failed, if its broker didn't delete the resource.

        :param request: The admin request.
        :param obj_display: The row's string form.
        :param obj_id: The row's primary key.
        :returns: Django's response, or a redirect to the list with the error.
        """
        errors = getattr(request, DELETE_ERRORS_ATTRIBUTE, None)
        if not errors:
            return super().response_delete(request, obj_display, obj_id)
        for error in errors:
            self.message_user(request, error, level=messages.ERROR)
        opts = self.model._meta  # pylint: disable=protected-access
        changelist_url = reverse(f"{self.admin_site.name}:{opts.app_label}_{opts.model_name}_changelist")
        return HttpResponseRedirect(changelist_url)


class SmarterCustomerModelAdmin(SmarterModelAdminMixin):
    """
    The admin of an account's resources: staff see the rows of their own account.

    The admin site lets only staff in. Its list shows the rows of :meth:`get_queryset`: for a model of owned
    resources, those that the user has ownership permission for, by :func:`smarter_scoped_queryset`. An admin of
    any other model scopes its rows in its own ``get_queryset()``, e.g. by the ownership of a parent resource. A
    row may be viewed if it is in the list, and changed or deleted with ownership permission
    (:func:`smarter_has_ud_permission`). Only superusers add rows.
    """

    def get_queryset(self, request: HttpRequest):
        """
        Return the rows that the request's user may see.

        :param request: The admin request.
        :returns: The rows, scoped by :func:`smarter_scoped_queryset`.
        """
        queryset = super().get_queryset(request)
        user = smarter_admin_user(request)
        return smarter_scoped_queryset(queryset, user)

    def has_module_permission(self, request: HttpRequest) -> bool:
        """
        Show the app's module to any authenticated user.

        An anonymous visitor, e.g. of the admin's login page, gets False without a warning. Its
        ``request.user`` is a lazy ``AnonymousUser``, which is expected.

        :param request: The admin request.
        :returns: True if the request's resolved user is an authenticated User.
        """
        user = smarter_admin_user(request)
        return user is not None

    def has_view_permission(self, request: HttpRequest, obj=None):
        """
        Let a user view the list, whose rows :meth:`get_queryset` scopes, and each row in it.

        :param request: The admin request.
        :param obj: The row, or None for the list.
        :returns: True for a superuser; for another authenticated user, True for the list, and for a row of it.
        """
        user = smarter_admin_user(request)
        if user is None:
            return False
        if user.is_superuser:
            return True
        if obj is None:
            return True
        queryset = self.get_queryset(request)
        return smarter_queryset_contains(queryset, obj)

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Let superusers add rows, and no one else: resources are created with manifests.

        An anonymous user gets False without a warning.

        :param request: The admin request.
        :param obj: The parent row of an inline, or None.
        :returns: True for a superuser.
        """
        user = smarter_admin_user(request)
        if user is None:
            return False
        return user.is_superuser

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Let a user change a row they have ownership permission for.

        :param request: The admin request.
        :param obj: The row, or None for the list, which only a superuser may change.
        :returns: The result of :func:`smarter_has_ud_permission`.
        """
        return smarter_has_ud_permission(request, obj)

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Let a user delete a row they have ownership permission for.

        :param request: The admin request.
        :param obj: The row, or None for the list's delete action, which only a superuser may use.
        :returns: The result of :func:`smarter_has_ud_permission`.
        """
        return smarter_has_ud_permission(request, obj)


class SmarterStaffOnlyModelAdmin(SmarterCustomerModelAdmin):
    """
    :class:`SmarterCustomerModelAdmin`, which also checks that the user is staff at every step.

    The admin site already lets only staff in. This checks it again, for the models whose rows only an
    account's administrators should ever see, e.g. its contacts and its api keys.
    """

    def has_module_permission(self, request: HttpRequest) -> bool:
        """Override the default module permission logic to restrict access to staff users and superusers only."""
        return smarter_is_staff(request)

    def has_view_permission(self, request: HttpRequest, obj=None):
        """
        Let staff view the list, whose rows :meth:`get_queryset` scopes, and each row in it.

        :param request: The admin request.
        :param obj: The row, or None for the list.
        :returns: True if the user is staff and :meth:`SmarterCustomerModelAdmin.has_view_permission` agrees.
        """
        if not smarter_is_staff(request):
            return False
        return super().has_view_permission(request, obj)

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Let staff change a row they have ownership permission for.

        :param request: The admin request.
        :param obj: The object, or None for the model as a whole.
        :returns: True if the user has the permission.
        """
        if not smarter_is_staff(request):
            return False
        return smarter_has_ud_permission(request, obj)

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Let staff delete a row they have ownership permission for.

        :param request: The admin request.
        :param obj: The object, or None for the model as a whole.
        :returns: True if the user has the permission.
        """
        if not smarter_is_staff(request):
            return False
        return smarter_has_ud_permission(request, obj)


class SmarterSuperUserOnlyModelAdmin(SmarterModelAdminMixin):
    """Customized Django Admin console model class that restricts module access to superusers only."""

    def has_module_permission(self, request: HttpRequest) -> bool:
        """Override the default module permission logic to restrict access to superusers only."""
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser  # type: ignore

    def has_view_permission(self, request: HttpRequest, obj=None):
        """
        Override the default view permission logic to restrict access to superusers only.

        :param request: The admin request.
        :param obj: The object, or None for the model as a whole.
        :returns: True if the user has the permission.
        """
        user = get_resolved_user(request.user)  # type: ignore
        if not isinstance(user, User):
            logger.warning("Unexpected user type: %s", type(user))
            return False
        return user.is_superuser

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Override the default add permission logic to restrict access to superusers only.

        :param request: The admin request.
        :param obj: The object, or None for the model as a whole.
        :returns: True if the user has the permission.
        """
        user = get_resolved_user(request.user)  # type: ignore
        if not isinstance(user, User):
            logger.warning("Unexpected user type: %s", type(user))
            return False
        return user.is_superuser

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Override the default change permission logic to restrict access to superusers only.

        :param request: The admin request.
        :param obj: The object, or None for the model as a whole.
        :returns: True if the user has the permission.
        """
        user = get_resolved_user(request.user)  # type: ignore
        if not isinstance(user, User):
            logger.warning("Unexpected user type: %s", type(user))
            return False
        return user.is_superuser

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Override the default delete permission logic to restrict access to superusers only.

        :param request: The admin request.
        :param obj: The object, or None for the model as a whole.
        :returns: True if the user has the permission.
        """
        user = get_resolved_user(request.user)  # type: ignore
        if not isinstance(user, User):
            logger.warning("Unexpected user type: %s", type(user))
            return False
        return user.is_superuser


class SmarterAutoModelAdmin(SmarterSuperUserOnlyModelAdmin):
    """
    A superuser-only admin whose list is built from its model's fields, by :func:`smarter_auto_model_admin`.

    :mod:`smarter.urls.console` registers one for each model that has no admin of its own, e.g. a third-party
    app's.
    """


def smarter_auto_search_field(field: models.Field) -> Optional[str]:
    """
    Return what a list searches for one of its model's fields, or None.

    A short text field without choices is searched, unless it holds a credential, a hash or a version (see
    :data:`UNSEARCHABLE_FIELD_NAMES` and :data:`UNSEARCHABLE_FIELD_SUFFIXES`). A foreign key is searched by the
    related row's ``name``, or its ``username``, if it has one.

    :param field: A concrete field of the model.
    :returns: The search field, e.g. ``title`` or ``user__username``, or None.
    """
    if field.is_relation:
        related_model = field.related_model
        if not isinstance(related_model, type):
            return None
        related_names = [related.name for related in related_model._meta.concrete_fields]  # pylint: disable=W0212
        if "name" in related_names:
            return f"{field.name}__name"
        if "username" in related_names:
            return f"{field.name}__username"
        return None
    if not isinstance(field, models.CharField):
        return None
    if field.choices:
        return None
    if field.name in UNSEARCHABLE_FIELD_NAMES:
        return None
    if field.name.endswith(UNSEARCHABLE_FIELD_SUFFIXES):
        return None
    return field.name


def smarter_auto_model_admin(model: type[models.Model]) -> type[SmarterAutoModelAdmin]:
    """
    Return a :class:`SmarterAutoModelAdmin` for a model, whose list is built from the model's fields.

    Its list shows up to :data:`AUTO_LIST_DISPLAY_LIMIT` of the model's short fields, filters by its boolean and
    choice fields, searches the fields that :func:`smarter_auto_search_field` returns, and has a date hierarchy of
    ``created_at``. Its timestamps are read-only.

    :param model: The model.
    :returns: A subclass of :class:`SmarterAutoModelAdmin`, with the model's options as its class attributes.
    """
    list_display: list[str] = []
    list_filter: list[str] = []
    search_fields: list[str] = []
    readonly_fields: list[str] = []
    field_names: list[str] = []
    for field in model._meta.concrete_fields:  # pylint: disable=protected-access
        field_names.append(field.name)
        is_long = isinstance(field, (models.TextField, models.JSONField, models.BinaryField))
        if not is_long and len(list_display) < AUTO_LIST_DISPLAY_LIMIT:
            list_display.append(field.name)
        if isinstance(field, models.BooleanField) or field.choices:
            list_filter.append(field.name)
        search_field = smarter_auto_search_field(field)
        if search_field:
            search_fields.append(search_field)
        if field.name in ("created_at", "updated_at"):
            readonly_fields.append(field.name)
    if not list_display:
        list_display = ["__str__"]
    date_hierarchy = None
    if "created_at" in field_names:
        date_hierarchy = "created_at"
    attributes = {
        "__module__": __name__,
        "__doc__": f"The admin of {model.__name__}, built from its fields.",
        "list_display": list_display,
        "list_filter": list_filter,
        "search_fields": search_fields,
        "readonly_fields": readonly_fields,
        "date_hierarchy": date_hierarchy,
    }
    admin_class = type(f"{model.__name__}AutoAdmin", (SmarterAutoModelAdmin,), attributes)
    return admin_class


class RestrictedAdminSite(admin.AdminSite):
    """Custom admin site that restricts access to certain apps and models and modifies the admin console header title."""

    site_header = SITE_HEADER

    def has_all_permission(self, request):
        """
        Whether the request's user is authenticated.

        :param request: The admin request.
        :returns: True if the user is authenticated.
        """
        return request.user.is_authenticated

    def each_context(self, request: HttpRequest):
        """
        Return the admin's template context, whose header names the request's user's role.

        The header is computed for each request and put in its context, never kept on the site: the site is one
        object, which concurrent requests share.

        :param request: The admin request.
        :returns: The template context of every admin page.
        """
        context = super().each_context(request)
        role = smarter_admin_role(request)
        context["site_header"] = SITE_HEADER + " (" + role + ")"
        return context


# Register the custom admin site
smarter_restricted_admin_site = RestrictedAdminSite(name="restricted_admin_site")


class EmailContactListAdmin(SmarterSuperUserOnlyModelAdmin):
    """
    Custom admin for the EmailContactList model: the emails that the landing page collected.

    They belong to no account, so only superusers see them.
    """

    list_display = ["email", "created_at", "updated_at"]
    ordering = ("-created_at",)
    search_fields = ["email"]
    date_hierarchy = "created_at"


class LogEntryAdmin(SmarterSuperUserOnlyModelAdmin):
    """
    The admin's own audit log, Django's :class:`~django.contrib.admin.models.LogEntry`, read-only, for superusers.

    Django writes an entry for each add, change and delete made in the admin: who, when, which row and what
    changed. Changes made with manifests are journaled in the Smarter Journal instead.
    """

    list_display = ["action_time", "user", "content_type", "object_repr", "action_flag", "change_message"]
    list_filter = ["action_flag", "content_type"]
    search_fields = ["object_repr", "change_message", "user__username"]
    date_hierarchy = "action_time"
    ordering = ["-action_time"]

    def get_readonly_fields(self, request, obj=None):
        """
        Make every field read-only.

        :param request: The admin request.
        :param obj: The entry, or None.
        :returns: Every field's name.
        """
        return [field.name for field in LogEntry._meta.fields]  # pylint: disable=protected-access

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Never add an entry by hand: Django writes them.

        :param request: The admin request.
        :param obj: Unused.
        :returns: False.
        """
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Never change an entry: the log is an audit trail.

        :param request: The admin request.
        :param obj: The entry, or None.
        :returns: False.
        """
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Never delete an entry: the log is an audit trail.

        :param request: The admin request.
        :param obj: The entry, or None.
        :returns: False.
        """
        return False


smarter_restricted_admin_site.register(EmailContactList, EmailContactListAdmin)
smarter_restricted_admin_site.register(LogEntry, LogEntryAdmin)
