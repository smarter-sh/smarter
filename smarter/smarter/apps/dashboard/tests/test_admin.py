"""
Test :mod:`smarter.apps.dashboard.admin`: the admin console's permission helpers, its ModelAdmin base classes,.

the mixin that every Smarter admin shares, and RestrictedAdminSite.

The users are the account's admin, who is a superuser, its non-admin user, a staff user of the same account, a
staff user of another account (the outsider), and an anonymous user. The resources are an api key that the
account's admin owns, a Guardrail that an LLMClient uses, and a Guardrail that nothing uses.
"""

import copy
import io
import zipfile
from http import HTTPStatus
from unittest.mock import MagicMock, patch

from django.contrib.admin import widgets
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.test import Client, RequestFactory
from django.urls import reverse
from django.utils.functional import SimpleLazyObject

from smarter.apps.account.models import Account, AccountContact, UserProfile
from smarter.apps.account.tests.factories import (
    factory_account_teardown,
    mortal_user_factory,
)
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.admin import (
    DELETE_ERRORS_ATTRIBUTE,
    SITE_HEADER,
    EmailContactListAdmin,
    LogEntryAdmin,
    RestrictedAdminSite,
    SmarterCustomerModelAdmin,
    SmarterStaffOnlyModelAdmin,
    SmarterSuperUserOnlyModelAdmin,
    smarter_admin_account_ids,
    smarter_admin_role,
    smarter_admin_user,
    smarter_auto_model_admin,
    smarter_auto_search_field,
    smarter_has_ud_permission,
    smarter_is_staff,
    smarter_queryset_contains,
    smarter_raw_id_fields,
    smarter_resource_kind,
    smarter_restricted_admin_site,
    smarter_scoped_queryset,
)
from smarter.apps.dashboard.models import EmailContactList
from smarter.apps.guardrail.models import Guardrail
from smarter.apps.guardrail.tests.base_classes import GUARDRAIL_DEFAULTS
from smarter.apps.infrastructure.models import InfrastructureResource
from smarter.apps.llmclient.models import (
    LLMClient,
    LLMClientCustomDomainDNS,
    LLMClientGuardrails,
)
from smarter.apps.orchestrator.models import OrchestrationStep
from smarter.lib.drf.models import SmarterAuthToken

PERMISSIONS = ("has_view_permission", "has_change_permission", "has_delete_permission")

UNSEARCHED_MODELS = frozenset(
    (
        "doodle.DoodleArtwork",
        "doodle.DoodleEditorRun",
        "journal.SAMJournalBlob",
        "sessions.Session",
    )
)
"""The models of the admin console whose lists have no search box: they have no text worth searching, or only secrets."""


def concrete_field(model: type[models.Model], name: str) -> models.Field:
    """Return a model's concrete field by its name."""
    for field in model._meta.concrete_fields:  # pylint: disable=protected-access
        if field.name == name:
            return field
    raise LookupError(name)


def admin_url(model, page: str, *args) -> str:
    """Return the url of a model's admin page, e.g. its ``changelist``, on the restricted admin site."""
    opts = model._meta  # pylint: disable=protected-access
    return reverse(f"{smarter_restricted_admin_site.name}:{opts.app_label}_{opts.model_name}_{page}", args=args)


# pylint: disable=too-many-public-methods
class TestDashboardAdmin(TestAccountMixin):
    """Test the admin console's role based access control, and the mixin of every Smarter admin."""

    api_key: SmarterAuthToken
    staff_user: User
    staff_profile: UserProfile
    outsider: User
    outsider_account: Account
    outsider_profile: UserProfile
    guardrail: Guardrail
    llmclient: LLMClient

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_key, _ = SmarterAuthToken.objects.create(  # type: ignore[misc]
            user_profile=cls.user_profile,
            name="test_dashboard_admin_api_key",
            user=cls.admin_user,
            description="test dashboard admin",
        )
        cls.staff_user, _, cls.staff_profile = mortal_user_factory(account=cls.account)
        cls.staff_user.is_staff = True
        cls.staff_user.save()
        cls.outsider, cls.outsider_account, cls.outsider_profile = mortal_user_factory()
        cls.outsider.is_staff = True
        cls.outsider.save()
        cls.guardrail = Guardrail.objects.create(
            name=f"test_admin_{cls.hash_suffix}",
            user_profile=cls.user_profile,
            **copy.deepcopy(GUARDRAIL_DEFAULTS),
        )
        cls.llmclient = LLMClient.objects.create(name=f"test_admin_{cls.hash_suffix}", user_profile=cls.user_profile)
        LLMClientGuardrails.objects.create(llmclient=cls.llmclient, guardrail=cls.guardrail)

    @classmethod
    def tearDownClass(cls):
        LLMClientGuardrails.objects.filter(guardrail=cls.guardrail).delete()
        LLMClient.objects.filter(pk=cls.llmclient.pk).delete()
        Guardrail.objects.filter(user_profile=cls.user_profile).delete()
        SmarterAuthToken.objects.filter(pk=cls.api_key.pk).delete()
        factory_account_teardown(cls.staff_user, None, cls.staff_profile)
        factory_account_teardown(cls.outsider, cls.outsider_account, cls.outsider_profile)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        # an unsaved user, so that is_staff without is_superuser needs no database row.
        self.unsaved_staff_user = User(username="test_dashboard_admin_staff", is_staff=True, is_superuser=False)

    def request(self, user):
        request = RequestFactory().get("/admin/")
        request.user = user
        return request

    def unused_guardrail(self) -> Guardrail:
        """Return a new Guardrail that nothing uses, deleted after the test."""
        guardrail = Guardrail.objects.create(
            name=f"test_admin_unused_{self.hash_suffix}",
            user_profile=self.user_profile,
            **copy.deepcopy(GUARDRAIL_DEFAULTS),
        )
        self.addCleanup(Guardrail.objects.filter(pk=guardrail.pk).delete)
        return guardrail

    def client_for(self, user) -> Client:
        """Return a client signed in as the user."""
        client = Client()
        client.force_login(user)
        self.addCleanup(client.logout)
        return client

    # -------------------------------------------------------------------------
    # helpers
    # -------------------------------------------------------------------------
    def test_smarter_admin_user(self):
        self.assertEqual(smarter_admin_user(self.request(self.admin_user)), self.admin_user)
        self.assertIsNone(smarter_admin_user(self.request(AnonymousUser())))
        self.assertIsNone(smarter_admin_user(RequestFactory().get("/admin/")))
        request = self.request(self.admin_user)
        with patch("smarter.apps.dashboard.admin.get_resolved_user", return_value=None):
            with self.assertLogs("smarter.apps.dashboard.admin", level="WARNING"):
                self.assertIsNone(smarter_admin_user(request))

    def test_smarter_is_staff(self):
        self.assertTrue(smarter_is_staff(self.request(self.admin_user)))
        self.assertTrue(smarter_is_staff(self.request(self.unsaved_staff_user)))
        self.assertFalse(smarter_is_staff(self.request(self.non_admin_user)))
        self.assertFalse(smarter_is_staff(self.request(AnonymousUser())))

    def test_smarter_has_ud_permission(self):
        """Test that a superuser can change anything, and another user only a resource they own, never an account or user."""
        self.assertTrue(smarter_has_ud_permission(self.request(self.admin_user), self.account))
        self.assertFalse(smarter_has_ud_permission(self.request(AnonymousUser()), self.api_key))
        for obj in (self.account, self.non_admin_user, self.non_admin_user_profile, None, object()):
            with self.subTest(obj=obj):
                self.assertFalse(smarter_has_ud_permission(self.request(self.non_admin_user), obj))
        self.assertFalse(smarter_has_ud_permission(self.request(self.non_admin_user), self.api_key))
        self.assertTrue(smarter_has_ud_permission(self.request(self.staff_user), self.api_key))
        self.assertFalse(smarter_has_ud_permission(self.request(self.outsider), self.api_key))

        request = RequestFactory().get("/admin/")
        request.user = type("NotAUser", (), {"is_authenticated": True})()
        self.assertFalse(smarter_has_ud_permission(request, self.api_key))

    def test_smarter_scoped_queryset(self):
        """A superuser sees every row; staff, the owned resources of their own account; no one else, nothing."""
        tokens = SmarterAuthToken.objects.all()
        self.assertTrue(smarter_scoped_queryset(tokens, self.admin_user).filter(pk=self.api_key.pk).exists())
        self.assertTrue(smarter_scoped_queryset(tokens, self.staff_user).filter(pk=self.api_key.pk).exists())
        self.assertFalse(smarter_scoped_queryset(tokens, self.outsider).filter(pk=self.api_key.pk).exists())
        self.assertFalse(smarter_scoped_queryset(tokens, None).exists())
        # a model of unowned rows is returned as it is: its admin scopes it.
        contacts = EmailContactList.objects.all()
        self.assertEqual(str(smarter_scoped_queryset(contacts, self.outsider).query), str(contacts.query))

    def test_smarter_queryset_contains(self):
        tokens = SmarterAuthToken.objects.all()
        self.assertTrue(smarter_queryset_contains(tokens, self.api_key))
        self.assertFalse(smarter_queryset_contains(tokens, self.account))
        self.assertFalse(smarter_queryset_contains(tokens, SmarterAuthToken()))
        self.assertFalse(smarter_queryset_contains(tokens, object()))

    def test_smarter_admin_account_ids(self):
        self.assertEqual(list(smarter_admin_account_ids(self.staff_user)), [{"account_id": self.account.pk}])

    def test_smarter_raw_id_fields(self):
        """Foreign keys to users, user profiles and accounts are shown as ids; others, as Django shows them."""
        self.assertEqual(set(smarter_raw_id_fields(SmarterAuthToken)), {"user", "user_profile"})
        self.assertEqual(smarter_raw_id_fields(LLMClientGuardrails), ())
        self.assertEqual(smarter_raw_id_fields(EmailContactList), ())

    def test_smarter_resource_kind(self):
        self.assertEqual(smarter_resource_kind(self.guardrail), "Guardrail")
        self.assertIsNone(smarter_resource_kind(EmailContactList(email="test@example.com")))
        with patch("smarter.apps.api.v1.cli.brokers.Brokers.get_broker", return_value=None):
            self.assertIsNone(smarter_resource_kind(self.guardrail))

    def test_smarter_admin_role(self):
        self.assertEqual(smarter_admin_role(self.request(AnonymousUser())), "guest")
        self.assertEqual(smarter_admin_role(self.request(self.admin_user)), "superuser")
        self.assertEqual(smarter_admin_role(self.request(self.unsaved_staff_user)), "account admin")
        self.non_admin_user.first_name, self.non_admin_user.last_name = "Ada", "Lovelace"
        self.assertEqual(smarter_admin_role(self.request(self.non_admin_user)), "customer - Ada Lovelace")
        not_a_user = MagicMock(is_authenticated=True)
        with patch("smarter.apps.dashboard.admin.get_resolved_user", return_value=not_a_user):
            with self.assertLogs("smarter.apps.dashboard.admin", level="WARNING"):
                self.assertEqual(smarter_admin_role(self.request(self.admin_user)), "unknown")

    # -------------------------------------------------------------------------
    # permission tiers
    # -------------------------------------------------------------------------
    def test_customer_model_admin(self):
        """Staff see and change their own account's api key; the outsider sees the list, but not the key."""
        model_admin = SmarterCustomerModelAdmin(SmarterAuthToken, RestrictedAdminSite())
        admin_request = self.request(self.admin_user)
        staff_request = self.request(self.staff_user)
        outsider_request = self.request(self.outsider)
        anonymous_request = self.request(AnonymousUser())

        self.assertTrue(model_admin.has_module_permission(admin_request))
        self.assertTrue(model_admin.has_module_permission(staff_request))
        self.assertFalse(model_admin.has_module_permission(anonymous_request))
        self.assertTrue(model_admin.has_add_permission(admin_request))
        self.assertFalse(model_admin.has_add_permission(staff_request))
        self.assertFalse(model_admin.has_add_permission(anonymous_request))

        # the list: staff may view it, and only a superuser may change it or use its delete action.
        self.assertTrue(model_admin.has_view_permission(staff_request, None))
        self.assertTrue(model_admin.has_view_permission(outsider_request, None))
        self.assertFalse(model_admin.has_view_permission(anonymous_request, None))
        self.assertFalse(model_admin.has_change_permission(staff_request, None))
        self.assertFalse(model_admin.has_delete_permission(staff_request, None))

        for permission in PERMISSIONS:
            with self.subTest(permission=permission):
                check = getattr(model_admin, permission)
                self.assertTrue(check(admin_request, self.api_key))
                self.assertTrue(check(staff_request, self.api_key))
                self.assertFalse(check(outsider_request, self.api_key))
                self.assertFalse(check(staff_request, Account()))
                self.assertFalse(check(anonymous_request, self.api_key))

        self.assertTrue(model_admin.get_queryset(staff_request).filter(pk=self.api_key.pk).exists())
        self.assertFalse(model_admin.get_queryset(outsider_request).filter(pk=self.api_key.pk).exists())
        self.assertFalse(model_admin.get_queryset(anonymous_request).exists())

    def test_customer_model_admin_anonymous_user_is_not_a_warning(self):
        """An anonymous visitor of the admin, e.g. of its login page, gets no access and logs no warning (issue #979)."""
        model_admin = SmarterCustomerModelAdmin(EmailContactList, RestrictedAdminSite())
        # Django's request.user is a SimpleLazyObject, which wraps an AnonymousUser when no one is signed in.
        lazy_anonymous_user = SimpleLazyObject(AnonymousUser)
        for user in (AnonymousUser(), lazy_anonymous_user):
            with self.subTest(user=type(user).__name__):
                request = self.request(user)
                with self.assertNoLogs("smarter.apps.dashboard.admin", level="WARNING"):
                    self.assertFalse(model_admin.has_module_permission(request))
                    self.assertFalse(model_admin.has_add_permission(request))
                    self.assertFalse(model_admin.has_view_permission(request))

    def test_staff_only_model_admin(self):
        model_admin = SmarterStaffOnlyModelAdmin(SmarterAuthToken, RestrictedAdminSite())
        admin_request = self.request(self.admin_user)
        staff_request = self.request(self.staff_user)
        user_request = self.request(self.non_admin_user)

        self.assertTrue(model_admin.has_module_permission(admin_request))
        self.assertTrue(model_admin.has_module_permission(staff_request))
        self.assertFalse(model_admin.has_module_permission(user_request))
        self.assertTrue(model_admin.has_add_permission(admin_request))
        self.assertFalse(model_admin.has_add_permission(staff_request))
        self.assertFalse(model_admin.has_add_permission(self.request(AnonymousUser())))
        self.assertTrue(model_admin.has_view_permission(staff_request, None))
        self.assertFalse(model_admin.has_view_permission(user_request, None))
        for permission in PERMISSIONS:
            with self.subTest(permission=permission):
                check = getattr(model_admin, permission)
                self.assertTrue(check(admin_request, self.api_key))
                self.assertTrue(check(staff_request, self.api_key))
                self.assertFalse(check(user_request, self.api_key))
                self.assertFalse(check(self.request(self.outsider), self.api_key))

    def test_superuser_only_model_admin(self):
        model_admin = SmarterSuperUserOnlyModelAdmin(EmailContactList, RestrictedAdminSite())
        self.assertTrue(model_admin.has_module_permission(self.request(self.admin_user)))
        self.assertFalse(model_admin.has_module_permission(self.request(self.staff_user)))
        self.assertFalse(model_admin.has_module_permission(self.request(AnonymousUser())))
        for permission in PERMISSIONS + ("has_add_permission",):
            with self.subTest(permission=permission):
                check = getattr(model_admin, permission)
                self.assertTrue(check(self.request(self.admin_user), self.api_key))
                self.assertFalse(check(self.request(self.staff_user), self.api_key))
                self.assertFalse(check(self.request(AnonymousUser()), self.api_key))

    def test_platform_wide_models_are_superuser_only(self):
        """Rows that belong to no account, and read-only ledgers, are hidden from staff, or read-only for all."""
        site = smarter_restricted_admin_site
        staff_request = self.request(self.staff_user)
        admin_request = self.request(self.admin_user)
        for model in (EmailContactList, LogEntry):
            with self.subTest(model=model.__name__):
                self.assertFalse(site._registry[model].has_module_permission(staff_request))  # pylint: disable=W0212
        read_only_models: tuple[type[models.Model], ...] = (LogEntry, InfrastructureResource, LLMClientCustomDomainDNS)
        for read_only_model in read_only_models:
            model_admin = site._registry[read_only_model]  # pylint: disable=protected-access
            with self.subTest(model=read_only_model.__name__):
                self.assertFalse(model_admin.has_add_permission(admin_request))
                self.assertFalse(model_admin.has_change_permission(admin_request))
                self.assertFalse(model_admin.has_delete_permission(admin_request))
        self.assertIsInstance(site._registry[LogEntry], LogEntryAdmin)  # pylint: disable=protected-access
        self.assertIsInstance(site._registry[EmailContactList], EmailContactListAdmin)  # pylint: disable=W0212

    def test_staff_see_nothing_of_another_account(self):
        """A staff user of an account that owns nothing sees no other account's rows in any list of the admin."""
        request = self.request(self.outsider)
        site = smarter_restricted_admin_site
        checked = 0
        for model, model_admin in site._registry.items():  # pylint: disable=protected-access
            if not model_admin.has_module_permission(request):
                continue
            if not model_admin.has_view_permission(request):
                continue
            queryset = model_admin.get_queryset(request)
            with self.subTest(model=model.__name__):
                checked += 1
                if model is User:
                    self.assertEqual(list(queryset), [self.outsider])
                elif model is Account:
                    self.assertEqual(list(queryset), [self.outsider_account])
                elif model is AccountContact:
                    self.assertFalse(queryset.exclude(account=self.outsider_account).exists())
                else:
                    self.assertFalse(queryset.exists(), f"{model.__name__}: {list(queryset[:3])}")
        self.assertGreater(checked, 20)

    def test_staff_admin_pages(self):
        """A staff user sees their account's Guardrail in the admin, and the outsider can't open it."""
        url = admin_url(Guardrail, "changelist")
        response = self.client_for(self.staff_user).get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn(self.guardrail.name, response.content.decode())

        index = self.client_for(self.staff_user).get(reverse(f"{smarter_restricted_admin_site.name}:index"))
        self.assertIn("Guardrails", index.content.decode())
        self.assertIn(f"{SITE_HEADER} (account admin)", index.content.decode())

        outsider = self.client_for(self.outsider)
        response = outsider.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotIn(self.guardrail.name, response.content.decode())
        response = outsider.get(admin_url(Guardrail, "change", self.guardrail.pk))
        self.assertNotEqual(response.status_code, HTTPStatus.OK)

    def test_account_admin_for_staff(self):
        """Staff see their own account, and its contacts, and no other."""
        account_admin = smarter_restricted_admin_site._registry[Account]  # pylint: disable=protected-access
        self.assertEqual(list(account_admin.get_queryset(self.request(self.staff_user))), [self.account])
        self.assertTrue(account_admin.get_queryset(self.request(self.admin_user)).filter(pk=self.outsider_account.pk))
        self.assertFalse(account_admin.get_queryset(self.request(AnonymousUser())).exists())
        contact_admin = smarter_restricted_admin_site._registry[AccountContact]  # pylint: disable=protected-access
        contacts = contact_admin.get_queryset(self.request(self.staff_user))
        self.assertFalse(contacts.exclude(account=self.account).exists())
        self.assertFalse(contact_admin.get_queryset(self.request(AnonymousUser())).exists())

    # -------------------------------------------------------------------------
    # the site's header
    # -------------------------------------------------------------------------
    def test_restricted_admin_site(self):
        """Test that the admin console's header names the user's role, in each request's own context."""
        site = RestrictedAdminSite()
        self.assertTrue(site.has_all_permission(self.request(self.admin_user)))
        self.assertFalse(site.has_all_permission(self.request(AnonymousUser())))

        self.non_admin_user.first_name, self.non_admin_user.last_name = "Ada", "Lovelace"
        customer_context = site.each_context(self.request(self.non_admin_user))
        admin_context = site.each_context(self.request(self.admin_user))
        guest_context = site.each_context(self.request(AnonymousUser()))
        self.assertEqual(customer_context["site_header"], f"{SITE_HEADER} (customer - Ada Lovelace)")
        self.assertEqual(admin_context["site_header"], f"{SITE_HEADER} (superuser)")
        self.assertEqual(guest_context["site_header"], f"{SITE_HEADER} (guest)")
        # the site is shared by every request, so no request's role is kept on it.
        self.assertEqual(site.site_header, SITE_HEADER)
        self.assertFalse(hasattr(site, "role"))

    # -------------------------------------------------------------------------
    # the mixin: lists and forms
    # -------------------------------------------------------------------------
    def test_get_list_select_related(self):
        """A list joins the foreign keys that it shows, and a user profile's user and account."""
        guardrail_admin = smarter_restricted_admin_site._registry[Guardrail]  # pylint: disable=protected-access
        self.assertEqual(
            guardrail_admin.get_list_select_related(self.request(self.admin_user)),
            ["user_profile", "user_profile__user", "user_profile__account"],
        )
        email_admin = EmailContactListAdmin(EmailContactList, RestrictedAdminSite())
        self.assertFalse(email_admin.get_list_select_related(self.request(self.admin_user)))

        class OwnSelectRelatedAdmin(SmarterSuperUserOnlyModelAdmin):
            list_select_related = ["user"]

        own = OwnSelectRelatedAdmin(SmarterAuthToken, RestrictedAdminSite())
        self.assertEqual(own.get_list_select_related(self.request(self.admin_user)), ["user"])

    def test_raw_id_fields(self):
        """A form shows a foreign key to a large table as an id, unless the admin names its own raw id fields."""
        model_admin = SmarterSuperUserOnlyModelAdmin(SmarterAuthToken, RestrictedAdminSite())
        self.assertEqual(set(model_admin.smarter_raw_id_field_names()), {"user", "user_profile"})
        request = self.request(self.admin_user)
        user_field = SmarterAuthToken._meta.get_field("user")  # pylint: disable=protected-access
        assert isinstance(user_field, models.ForeignKey)
        form_field = model_admin.formfield_for_foreignkey(user_field, request)
        assert form_field is not None
        self.assertIsInstance(form_field.widget, widgets.ForeignKeyRawIdWidget)

        class OwnRawIdAdmin(SmarterSuperUserOnlyModelAdmin):
            raw_id_fields = ("user",)

        own = OwnRawIdAdmin(SmarterAuthToken, RestrictedAdminSite())
        self.assertEqual(own.smarter_raw_id_field_names(), ("user",))

        groups = User._meta.get_field("groups")  # pylint: disable=protected-access
        assert isinstance(groups, models.ManyToManyField)
        user_admin = SmarterSuperUserOnlyModelAdmin(User, RestrictedAdminSite())
        groups_field = user_admin.formfield_for_manytomany(groups, request)
        assert groups_field is not None
        self.assertNotIsInstance(groups_field.widget, widgets.ManyToManyRawIdWidget)

        class GroupsRawIdAdmin(SmarterSuperUserOnlyModelAdmin):
            raw_id_fields = ("groups",)

        groups_admin = GroupsRawIdAdmin(User, RestrictedAdminSite())
        raw_groups_field = groups_admin.formfield_for_manytomany(groups, request)
        assert raw_groups_field is not None
        self.assertIsInstance(raw_groups_field.widget, widgets.ManyToManyRawIdWidget)

    def test_auto_model_admin(self):
        """The fallback admin builds its list, filters, search and date hierarchy from the model's fields."""
        model_admin = smarter_auto_model_admin(OrchestrationStep)(OrchestrationStep, RestrictedAdminSite())
        self.assertEqual(type(model_admin).__name__, "OrchestrationStepAutoAdmin")
        self.assertIn("status", model_admin.list_display)
        self.assertNotIn("error_message", model_admin.list_display)
        self.assertIn("status", model_admin.list_filter)
        self.assertEqual(model_admin.date_hierarchy, "created_at")
        self.assertIn("created_at", model_admin.readonly_fields)
        self.assertFalse(model_admin.has_view_permission(self.request(self.staff_user)))

        content_type_admin = smarter_auto_model_admin(ContentType)(ContentType, RestrictedAdminSite())
        self.assertEqual(list(content_type_admin.list_display), ["id", "app_label", "model"])
        self.assertIsNone(content_type_admin.date_hierarchy)

        self.assertEqual(smarter_auto_model_admin(User).search_fields, ["username", "first_name", "last_name", "email"])

    def test_every_list_has_a_search_box(self):
        """Every list of the admin console searches something, except the lists in UNSEARCHED_MODELS."""
        request = self.request(self.admin_user)
        missing = []
        for model, model_admin in smarter_restricted_admin_site._registry.items():  # pylint: disable=W0212
            label = model._meta.label  # pylint: disable=protected-access
            if label in UNSEARCHED_MODELS:
                continue
            if not model_admin.get_search_fields(request):
                missing.append(label)
        self.assertEqual(sorted(missing), [])

    def test_owned_resources_are_searched_by_default(self):
        """The list of an owned resource searches its name, description and owner, unless its admin says otherwise."""
        request = self.request(self.admin_user)
        token_admin = SmarterCustomerModelAdmin(SmarterAuthToken, RestrictedAdminSite())
        self.assertEqual(
            token_admin.get_search_fields(request), ("name", "description", "user_profile__user__username")
        )
        self.assertEqual(
            SmarterCustomerModelAdmin(EmailContactList, RestrictedAdminSite()).get_search_fields(request), ()
        )
        guardrail_admin = smarter_restricted_admin_site._registry[Guardrail]  # pylint: disable=protected-access
        self.assertEqual(list(guardrail_admin.get_search_fields(request)), ["name", "description"])

    def test_smarter_auto_search_field(self):
        """A short text field, or a foreign key's name or username, is searched; a credential or a hash isn't."""
        self.assertEqual(smarter_auto_search_field(concrete_field(ContentType, "model")), "model")
        self.assertIsNone(smarter_auto_search_field(concrete_field(ContentType, "id")))
        self.assertIsNone(smarter_auto_search_field(concrete_field(User, "password")))
        self.assertIsNone(smarter_auto_search_field(concrete_field(SmarterAuthToken, "digest")))
        self.assertIsNone(smarter_auto_search_field(concrete_field(SmarterAuthToken, "token_key")))
        self.assertEqual(smarter_auto_search_field(concrete_field(SmarterAuthToken, "user")), "user__username")
        self.assertEqual(smarter_auto_search_field(concrete_field(OrchestrationStep, "prompt")), "prompt__name")
        self.assertIsNone(smarter_auto_search_field(concrete_field(OrchestrationStep, "run")))
        self.assertIsNone(smarter_auto_search_field(concrete_field(OrchestrationStep, "status")))

    def test_log_entry_admin_page(self):
        response = self.client_for(self.admin_user).get(admin_url(LogEntry, "changelist"))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    # -------------------------------------------------------------------------
    # the mixin: export as manifests
    # -------------------------------------------------------------------------
    def test_export_action(self):
        """The export action is offered on a list of SAM resources, and nowhere else."""
        guardrail_admin = smarter_restricted_admin_site._registry[Guardrail]  # pylint: disable=protected-access
        self.assertIn("export_manifests", guardrail_admin.get_actions(self.request(self.staff_user)))
        email_admin = smarter_restricted_admin_site._registry[EmailContactList]  # pylint: disable=protected-access
        self.assertNotIn("export_manifests", email_admin.get_actions(self.request(self.admin_user)))
        popup = RequestFactory().get("/admin/", {"_popup": "1"})
        popup.user = self.admin_user
        self.assertNotIn("export_manifests", guardrail_admin.get_actions(popup))

        class NoActionsAdmin(SmarterSuperUserOnlyModelAdmin):
            actions = None

        no_actions = NoActionsAdmin(Guardrail, RestrictedAdminSite())
        self.assertEqual(no_actions.get_actions(self.request(self.admin_user)), {})

        no_view = SmarterSuperUserOnlyModelAdmin(Guardrail, RestrictedAdminSite())
        self.assertNotIn("export_manifests", no_view.get_actions(self.request(self.staff_user)))

    def test_export_one_manifest(self):
        """One selected resource downloads as its YAML manifest."""
        response = self.client_for(self.staff_user).post(
            admin_url(Guardrail, "changelist"),
            {"action": "export_manifests", "_selected_action": [self.guardrail.pk]},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "application/yaml")
        self.assertIn(".yaml", response["Content-Disposition"])
        content = response.content.decode()
        self.assertIn("kind: Guardrail", content)
        self.assertIn(f"name: {self.guardrail.name}", content)

    def test_export_manifests_as_zip(self):
        """Several selected resources download as a zip file of their manifests."""
        unused = self.unused_guardrail()
        response = self.client_for(self.admin_user).post(
            admin_url(Guardrail, "changelist"),
            {"action": "export_manifests", "_selected_action": [self.guardrail.pk, unused.pk]},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "application/zip")
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            names = archive.namelist()
        self.assertEqual(len(names), 2)
        for name in names:
            self.assertIn(f"/{self.account.account_number}/Guardrail/", name)

    def test_export_without_manifests(self):
        """A row with no manifest is reported, and an export of nothing shows the list again."""
        model_admin = SmarterSuperUserOnlyModelAdmin(LLMClientGuardrails, RestrictedAdminSite())
        model_admin.message_user = MagicMock()  # type: ignore[method-assign]
        request = self.request(self.admin_user)
        result = model_admin.export_manifests(request, LLMClientGuardrails.objects.filter(guardrail=self.guardrail))
        self.assertIsNone(result)
        model_admin.message_user.assert_called_once()

        guardrail_admin = SmarterSuperUserOnlyModelAdmin(Guardrail, RestrictedAdminSite())
        guardrail_admin.message_user = MagicMock()  # type: ignore[method-assign]
        with patch("smarter.apps.account.data_export.manifest_file", return_value=(None, "broken")):
            result = guardrail_admin.export_manifests(request, Guardrail.objects.filter(pk=self.guardrail.pk))
        self.assertIsNone(result)
        guardrail_admin.message_user.assert_called_once()

    # -------------------------------------------------------------------------
    # the mixin: deletes with the broker
    # -------------------------------------------------------------------------
    def test_delete_page_protects_a_resource_that_others_use(self):
        """The delete page lists the LLMClient that uses the Guardrail as protected, and doesn't delete it."""
        client = self.client_for(self.admin_user)
        url = admin_url(Guardrail, "delete", self.guardrail.pk)
        response = client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn(f"LLMClient {self.llmclient.name}, which depends on Guardrail", response.content.decode())
        client.post(url, {"post": "yes"})
        self.assertTrue(Guardrail.objects.filter(pk=self.guardrail.pk).exists())

    def test_delete_page_deletes_with_the_broker(self):
        """A Guardrail that nothing uses is deleted by its broker."""
        unused = self.unused_guardrail()
        with patch(
            "smarter.apps.dashboard.resource_detail.delete_with_broker", wraps=self.real_delete_with_broker()
        ) as delete:
            response = self.client_for(self.admin_user).post(admin_url(Guardrail, "delete", unused.pk), {"post": "yes"})
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        delete.assert_called_once()
        self.assertFalse(Guardrail.objects.filter(pk=unused.pk).exists())

    def real_delete_with_broker(self):
        """Return the real delete_with_broker, for a patch that wraps it."""
        # pylint: disable=import-outside-toplevel
        from smarter.apps.dashboard.resource_detail import delete_with_broker

        return delete_with_broker

    def test_delete_model_failure_shows_the_list_with_the_error(self):
        """When the broker doesn't delete the resource, the admin says so, instead of reporting a delete."""
        model_admin = SmarterSuperUserOnlyModelAdmin(Guardrail, smarter_restricted_admin_site)
        model_admin.message_user = MagicMock()  # type: ignore[method-assign]
        request = self.request(self.admin_user)
        unused = self.unused_guardrail()
        with patch("smarter.apps.dashboard.resource_detail.delete_with_broker", return_value="refused"):
            model_admin.delete_model(request, unused)
        self.assertEqual(getattr(request, DELETE_ERRORS_ATTRIBUTE), [f"Guardrail {unused} was not deleted: refused"])
        response = model_admin.response_delete(request, str(unused), unused.pk)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response["Location"], admin_url(Guardrail, "changelist"))
        model_admin.message_user.assert_called_once()
        self.assertTrue(Guardrail.objects.filter(pk=unused.pk).exists())

    def test_delete_model_of_a_row_without_a_kind(self):
        """A row that isn't a SAM resource is deleted as Django deletes it."""
        model_admin = SmarterSuperUserOnlyModelAdmin(EmailContactList, smarter_restricted_admin_site)
        contact = EmailContactList.objects.create(email=f"test-admin-{self.hash_suffix}@example.com")
        self.addCleanup(EmailContactList.objects.filter(pk=contact.pk).delete)
        model_admin.delete_model(self.request(self.admin_user), contact)
        self.assertFalse(EmailContactList.objects.filter(pk=contact.pk).exists())

    def test_delete_queryset(self):
        """The delete action deletes each SAM resource with its broker, reports a failure, and deletes other rows."""
        model_admin = SmarterSuperUserOnlyModelAdmin(Guardrail, smarter_restricted_admin_site)
        model_admin.message_user = MagicMock()  # type: ignore[method-assign]
        request = self.request(self.admin_user)
        unused = self.unused_guardrail()
        model_admin.delete_queryset(request, Guardrail.objects.filter(pk__in=[unused.pk, self.guardrail.pk]))
        self.assertFalse(Guardrail.objects.filter(pk=unused.pk).exists())
        self.assertTrue(Guardrail.objects.filter(pk=self.guardrail.pk).exists())
        model_admin.message_user.assert_called_once()

        contact_admin = SmarterSuperUserOnlyModelAdmin(EmailContactList, smarter_restricted_admin_site)
        contact = EmailContactList.objects.create(email=f"test-admin-bulk-{self.hash_suffix}@example.com")
        self.addCleanup(EmailContactList.objects.filter(pk=contact.pk).delete)
        contact_admin.delete_queryset(request, EmailContactList.objects.filter(pk=contact.pk))
        self.assertFalse(EmailContactList.objects.filter(pk=contact.pk).exists())
