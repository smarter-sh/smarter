"""Test the Django admin of Smarter annotations, :mod:`smarter.lib.annotation.admin`."""

from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.admin import smarter_restricted_admin_site
from smarter.lib.annotation.admin import AnnotationAdmin
from smarter.lib.annotation.models import Annotation


class TestAnnotationAdmin(TestAccountMixin):
    """Test that the admin can't move an annotation to another resource."""

    def test_resource_is_readonly_once_saved(self):
        """Test that content_type and object_id can be set on a new row, but not changed on a saved one."""
        model_admin = smarter_restricted_admin_site._registry[Annotation]  # pylint: disable=W0212
        self.assertIsInstance(model_admin, AnnotationAdmin)
        request = RequestFactory().get("/")
        request.user = self.admin_user
        new = model_admin.get_readonly_fields(request)
        self.assertNotIn("content_type", new)
        self.assertNotIn("object_id", new)
        saved = model_admin.get_readonly_fields(request, Annotation(pk=1))
        self.assertIn("content_type", saved)
        self.assertIn("object_id", saved)
        self.assertIn("prefix", saved)
