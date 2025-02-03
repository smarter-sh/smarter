"""Test SmarterRequestMixin."""

import unittest
import uuid

from django.contrib.auth.models import User
from django.test import Client, RequestFactory

from smarter.lib.django.request import SmarterRequestMixin


class TestSmarterRequestMixin(unittest.TestCase):
    """Test SmarterRequestMixin."""

    def setUp(self):
        self.client = Client()
        self.wsgi_request_factory = RequestFactory()
        random_username = f"testuser_{uuid.uuid4().hex[:8]}"
        self.user = User.objects.create_user(username=random_username, password="12345")

    def tearDown(self):
        self.user.delete()

    def test_unauthenticated_instantiation(self):
        self.client.login(username=self.user.username, password="12345")
        request = self.wsgi_request_factory.get("/")

        srm = SmarterRequestMixin(request)
        self.assertIsNotNone(srm.to_json())

    def test_authenticated_instantiation(self):
        self.client.login(username=self.user.username, password="12345")
        response = self.client.get("/")
        request = response.wsgi_request

        srm = SmarterRequestMixin(request)
        self.assertIsNotNone(srm.to_json())
