"""
Test :mod:`smarter.apps.dashboard.admin`: the admin console's permission helpers, its three.

ModelAdmin base classes, and RestrictedAdminSite.

The users are the account's admin, who is a superuser, its non-admin user, a staff user who is
not a superuser, and an anonymous user. The object is an api key that the account's admin owns.
"""

from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory

from smarter.apps.account.models import Account
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.admin import (
    RestrictedAdminSite,
    SmarterCustomerModelAdmin,
    SmarterStaffOnlyModelAdmin,
    SmarterSuperUserOnlyModelAdmin,
    smarter_has_ud_permission,
    smarter_is_staff,
)
from smarter.apps.dashboard.models import EmailContactList
from smarter.lib.drf.models import SmarterAuthToken

PERMISSIONS = ("has_view_permission", "has_change_permission", "has_delete_permission")


class TestDashboardAdmin(TestAccountMixin):
    """Test the admin console's role based access control."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_key, _ = SmarterAuthToken.objects.create(  # type: ignore[misc]
            user_profile=cls.user_profile,
            name="test_dashboard_admin_api_key",
            user=cls.admin_user,
            description="test dashboard admin",
        )

    @classmethod
    def tearDownClass(cls):
        SmarterAuthToken.objects.filter(pk=cls.api_key.pk).delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        # an unsaved user, so that is_staff without is_superuser needs no database row.
        self.staff_user = User(username="test_dashboard_admin_staff", is_staff=True, is_superuser=False)

    def request(self, user):
        request = RequestFactory().get("/admin/")
        request.user = user
        return request

    def test_smarter_is_staff(self):
        self.assertTrue(smarter_is_staff(self.request(self.admin_user)))
        self.assertTrue(smarter_is_staff(self.request(self.staff_user)))
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

        request = RequestFactory().get("/admin/")
        request.user = type("NotAUser", (), {"is_authenticated": True})()
        self.assertFalse(smarter_has_ud_permission(request, self.api_key))

    def test_customer_model_admin(self):
        model_admin = SmarterCustomerModelAdmin(EmailContactList, RestrictedAdminSite())
        admin_request = self.request(self.admin_user)
        user_request = self.request(self.non_admin_user)

        self.assertTrue(model_admin.has_module_permission(admin_request))
        self.assertTrue(model_admin.has_module_permission(user_request))
        self.assertFalse(model_admin.has_module_permission(self.request(AnonymousUser())))
        self.assertTrue(model_admin.has_add_permission(admin_request))
        self.assertFalse(model_admin.has_add_permission(user_request))
        self.assertFalse(model_admin.has_add_permission(self.request(AnonymousUser())))
        for permission in PERMISSIONS:
            with self.subTest(permission=permission):
                self.assertTrue(getattr(model_admin, permission)(admin_request, self.api_key))
                self.assertFalse(getattr(model_admin, permission)(user_request, Account()))
                self.assertFalse(getattr(model_admin, permission)(self.request(AnonymousUser()), self.api_key))

        # the account's non-admin user can read, but not change, the account admin's api key.
        self.assertEqual(
            model_admin.has_view_permission(user_request, self.api_key),
            SmarterAuthToken.objects.with_read_permission_for(user=self.non_admin_user)
            .filter(pk=self.api_key.pk)
            .exists(),
        )
        self.assertFalse(model_admin.has_view_permission(user_request, None))

    def test_staff_only_model_admin(self):
        model_admin = SmarterStaffOnlyModelAdmin(EmailContactList, RestrictedAdminSite())
        admin_request = self.request(self.admin_user)
        user_request = self.request(self.non_admin_user)

        self.assertTrue(model_admin.has_module_permission(admin_request))
        self.assertTrue(model_admin.has_module_permission(self.request(self.staff_user)))
        self.assertFalse(model_admin.has_module_permission(user_request))
        self.assertTrue(model_admin.has_add_permission(admin_request))
        self.assertFalse(model_admin.has_add_permission(self.request(self.staff_user)))
        self.assertFalse(model_admin.has_add_permission(self.request(AnonymousUser())))
        for permission in PERMISSIONS:
            with self.subTest(permission=permission):
                self.assertTrue(getattr(model_admin, permission)(admin_request, self.api_key))
                self.assertFalse(getattr(model_admin, permission)(user_request, self.api_key))

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

    def test_restricted_admin_site(self):
        """Test that the admin console's header names the user's role."""
        site = RestrictedAdminSite()
        self.assertTrue(site.has_all_permission(self.request(self.admin_user)))
        self.assertFalse(site.has_all_permission(self.request(AnonymousUser())))

        site.each_context(self.request(AnonymousUser()))
        self.assertEqual(site.role, "guest")
        site.each_context(self.request(self.admin_user))
        self.assertEqual(site.role, "superuser")
        site.each_context(self.request(self.staff_user))
        self.assertEqual(site.role, "account admin")
        self.non_admin_user.first_name, self.non_admin_user.last_name = "Ada", "Lovelace"
        site.each_context(self.request(self.non_admin_user))
        self.assertEqual(site.role, "customer - Ada Lovelace")
        self.assertIn("(customer - Ada Lovelace)", site.site_header)
