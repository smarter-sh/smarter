"""Test the Secret admin, :mod:`smarter.apps.secret.admin`."""

from unittest.mock import MagicMock

from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.admin import smarter_restricted_admin_site
from smarter.apps.secret.admin import CustomPasswordWidget, SecretAdmin
from smarter.apps.secret.models import Secret
from smarter.apps.secret.tests.factories import secret_factory

SECRET_VALUE = "test-secret-admin-value"


class TestSecretAdmin(TestAccountMixin):
    """Test the Secret admin form and model admin."""

    def setUp(self):
        super().setUp()
        self.secret = secret_factory(
            user_profile=self.user_profile,
            name=f"test_secret_admin_{self.hash_suffix}",
            description="test secret admin",
            value=SECRET_VALUE,
        )
        self.addCleanup(Secret.objects.filter(pk=self.secret.pk).delete)
        self.model_admin = SecretAdmin(Secret, smarter_restricted_admin_site)

    def request(self, user):
        request = RequestFactory().get("/")
        request.user = user
        return request

    def form_class(self, user, obj=None):
        """The admin's SecretAdminForm, which SecretAdmin.get_form() gives its model and user."""
        return self.model_admin.get_form(self.request(user), obj=obj)

    def test_form_without_user_is_read_only(self):
        """Test that a form without an authenticated user disables all of its fields."""
        anonymous = MagicMock(is_authenticated=False)
        form = self.form_class(anonymous, self.secret)(instance=self.secret)
        self.assertTrue(all(field.disabled for field in form.fields.values()))

    def test_form_masks_the_value_of_an_existing_secret(self):
        form = self.form_class(self.admin_user, self.secret)(instance=self.secret)
        self.assertEqual(form.fields["value"].initial, "********")
        self.assertFalse(form.fields["name"].disabled)

    def test_form_clean(self):
        """Test that the transient value is included in the cleaned data."""
        data = {
            "name": f"test_secret_admin_form_{self.hash_suffix}",
            "user_profile": self.user_profile.pk,
            "description": "test",
            "value": "new-value",
        }
        form_class = self.form_class(self.admin_user)
        form = form_class(data=data)
        form.is_valid()
        self.assertEqual(form.cleaned_data.get("value"), "new-value")

    def test_display_value(self):
        """Test that the owner sees the secret's value, and a user without permission sees it masked."""
        self.model_admin.request = self.request(self.admin_user)
        self.assertEqual(self.model_admin.display_value(self.secret), SECRET_VALUE)

        self.model_admin.request = self.request(self.non_admin_user)
        masked = self.model_admin.display_value(self.secret)
        self.assertNotEqual(masked, SECRET_VALUE)

        self.assertEqual(self.model_admin.display_value("not a secret"), "********")
        self.model_admin.request = object()
        self.assertEqual(self.model_admin.display_value(self.secret), "********")

    def test_get_form_injects_the_user(self):
        form_class = self.model_admin.get_form(self.request(self.admin_user), obj=self.secret)
        form = form_class(instance=self.secret)
        self.assertEqual(form.user, self.admin_user)

    def test_save_model_encrypts_the_value(self):
        form = MagicMock()
        form.cleaned_data = {"value": "changed-value"}
        self.model_admin.save_model(self.request(self.admin_user), self.secret, form, change=True)
        self.assertEqual(Secret.objects.get(pk=self.secret.pk).get_secret(update_last_accessed=False), "changed-value")

    def test_get_queryset(self):
        """Test that the queryset includes the user's secret, and is empty for an anonymous user."""
        qs = self.model_admin.get_queryset(self.request(self.admin_user))
        self.assertIn(self.secret, qs)
        anonymous = MagicMock(is_authenticated=False)
        self.assertFalse(self.model_admin.get_queryset(self.request(anonymous)).exists())

    def test_password_widget(self):
        self.assertIn("CHANGE PASSWORD", CustomPasswordWidget().render("password", "x"))
