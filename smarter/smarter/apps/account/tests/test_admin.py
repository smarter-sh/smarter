"""
Test the account app's model admins, :mod:`smarter.apps.account.admin`.

Each admin that the restricted admin site registers for the account app is asked for
its queryset and permissions, as a superuser, a staff user and a customer.
"""

from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory

from smarter.apps.account import admin as account_admin
from smarter.apps.account.models import Account, AccountContact, UserProfile
from smarter.apps.account.tests.factories import mortal_user_factory
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.secret.models import Secret


class TestAccountAdmin(TestAccountMixin):
    """Test the account app's model admins and smarter_filter_queryset_for_user_profile()."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.staff_user, _, cls.staff_user_profile = mortal_user_factory(account=cls.account)
        cls.staff_user.is_staff = True
        cls.staff_user.save()

    @classmethod
    def tearDownClass(cls):
        User.objects.filter(pk=cls.staff_user.pk).delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.admins = [
            model_admin
            for model, model_admin in account_admin.smarter_restricted_admin_site._registry.items()  # pylint: disable=protected-access
            if model._meta.app_label == "account" or model in (User,)
        ]

    def request(self, user):
        request = self.factory.get("/admin/")
        request.user = user
        return request

    def test_registered(self):
        self.assertGreaterEqual(len(self.admins), 9)

    def test_querysets_and_permissions(self):
        """Test that every admin answers each role without an error."""
        for user in (self.admin_user, self.staff_user, self.non_admin_user):
            request = self.request(user)
            for model_admin in self.admins:
                with self.subTest(admin=type(model_admin).__name__, user=user.username):
                    list(model_admin.get_queryset(request)[:5])
                    model_admin.has_module_permission(request)
                    model_admin.has_view_permission(request)
                    model_admin.has_add_permission(request)
                    model_admin.has_change_permission(request)
                    model_admin.has_delete_permission(request)
                    model_admin.get_readonly_fields(request)

    def test_superuser_sees_every_account(self):
        account_admin_instance = account_admin.smarter_restricted_admin_site._registry[
            Account
        ]  # pylint: disable=protected-access
        qs = account_admin_instance.get_queryset(self.request(self.admin_user))
        self.assertEqual(qs.count(), Account.objects.count())

    def test_filter_for_roles(self):
        """Test the filter for a superuser, a staff user and a customer."""
        contact = AccountContact.objects.create(
            account=self.account, email="test_admin_contact@example.com", first_name="A", last_name="B", welcomed=True
        )
        self.addCleanup(contact.delete)
        qs = UserProfile.objects.all()
        flt = account_admin.smarter_filter_queryset_for_user_profile
        self.assertEqual(flt(self.user_profile, qs).count(), qs.count())
        self.assertEqual(list(flt(self.staff_user_profile, UserProfile.objects.none())), [])
        # a model without a user_profile field, for a staff user and a customer.
        self.assertEqual(flt(self.staff_user_profile, AccountContact.objects.all()).count(), 0)
        self.assertEqual(flt(self.non_admin_user_profile, AccountContact.objects.all()).count(), 0)
        self.assertEqual(flt(self.staff_user_profile, qs, user_profile_filter=None).count(), 0)
        self.assertEqual(flt(self.non_admin_user_profile, qs, user_profile_filter=None).count(), 0)
        # a customer sees their own secrets, and their account admin's.
        mine = Secret.objects.create(
            user_profile=self.non_admin_user_profile, name="test_admin_mine", encrypted_value=Secret.encrypt("a")
        )
        shared = Secret.objects.create(
            user_profile=self.user_profile, name="test_admin_shared", encrypted_value=Secret.encrypt("b")
        )
        self.addCleanup(Secret.objects.filter(pk__in=[mine.pk, shared.pk]).delete)
        visible = flt(self.non_admin_user_profile, Secret.objects.all())
        self.assertIn(mine, visible)
        self.assertIn(shared, visible)
        visible = flt(self.non_admin_user_profile, Secret.objects.all(), account_filter="user_profile__account")
        self.assertIn(mine, visible)
        self.assertEqual(
            flt(self.non_admin_user_profile, Secret.objects.all(), account_filter="not_a_field").count(), 0
        )
        self.assertEqual(flt(self.staff_user_profile, Secret.objects.all()).count(), 0)

    def test_filter_without_user_profile(self):
        self.assertEqual(account_admin.smarter_filter_queryset_for_user_profile(None, Account.objects.all()).count(), 0)  # type: ignore[arg-type]

    def test_user_admin(self):
        """Test that staff may change only the users of their own account, and only superusers may delete users."""
        user_admin = account_admin.smarter_restricted_admin_site._registry[User]  # pylint: disable=protected-access
        staff = self.request(self.staff_user)
        self.assertTrue(user_admin.has_change_permission(staff, self.non_admin_user))
        self.assertFalse(user_admin.has_change_permission(staff, None))
        self.assertFalse(user_admin.has_delete_permission(staff))
        self.assertTrue(user_admin.has_delete_permission(self.request(self.admin_user)))
        self.assertFalse(user_admin.has_change_permission(self.request(self.non_admin_user), self.non_admin_user))
        self.assertFalse(user_admin.has_delete_permission(self.request(AnonymousUser())))
        self.assertFalse(user_admin.has_add_permission(staff))
        self.assertEqual(user_admin.profile_account(self.non_admin_user), self.account)
        users = user_admin.get_queryset(staff)
        self.assertIn(self.non_admin_user, users)

    def test_anonymous(self):
        request = self.request(AnonymousUser())
        user_profile_admin = account_admin.smarter_restricted_admin_site._registry[
            UserProfile
        ]  # pylint: disable=protected-access
        self.assertEqual(user_profile_admin.get_queryset(request).count(), 0)
        self.assertEqual(user_profile_admin.get_queryset(self.request(self.staff_user)).count(), 0)
