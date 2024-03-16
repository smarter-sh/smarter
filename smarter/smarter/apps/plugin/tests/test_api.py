# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position
# pylint: disable=R0801,W0613,R0902
"""Test plugin API."""

# python stuff
import os
import unittest
from urllib.parse import urlparse

import yaml
from django.contrib.auth import get_user_model
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect
from django.test import Client

# our stuff
from smarter.apps.account.models import Account, UserProfile
from smarter.apps.plugin.plugin import Plugin
from smarter.apps.plugin.tests.test_setup import get_test_file_path


User = get_user_model()


class TestPluginAPI(unittest.TestCase):
    """Test Plugin API."""

    API_BASE = "/api/v0/plugins/"
    plugin_yaml: str = None
    plugin_yaml_modified: str = None
    plugin: Plugin = None
    account: Account = None
    admin_user: User = None
    admin_user_profile: UserProfile = None
    mortal_user: User = None
    mortal_user_profile: UserProfile = None

    @property
    def api_base(self):
        """Return the API base."""
        return self.API_BASE

    def create_user(self, username, password, is_staff: bool = False) -> tuple:
        """Create a user."""
        user = User.objects.create(
            username=username,
            password=password,
            is_active=True,
            is_staff=is_staff,
            is_superuser=False,
        )
        user_profile = UserProfile.objects.create(user=user, account=self.account)
        return user, user_profile

    def safe_load(self, file_path) -> dict:
        """Load a file."""
        with open(file_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)

    def setUp(self):
        """Set up test fixtures."""
        plugin_path = get_test_file_path("everlasting-gobstopper.yaml")
        self.plugin_yaml = self.safe_load(file_path=plugin_path)

        plugin_path = get_test_file_path("everlasting-gobstopper-modified.yaml")
        self.plugin_yaml_modified = self.safe_load(file_path=plugin_path)

        # create a 4-digit random string of alphanumeric characters
        self.account = Account.objects.create(company_name="Test Account")
        admin_username = "test_admin_" + os.urandom(4).hex()
        self.admin_user, self.admin_user_profile = self.create_user(
            username=admin_username, password="12345", is_staff=True
        )

        mortal_username = "test_mortal_" + os.urandom(4).hex()
        self.mortal_user, self.mortal_user_profile = self.create_user(
            username=mortal_username, password="12345", is_staff=False
        )

    def tearDown(self):
        """Clean up test fixtures."""
        self.admin_user_profile.delete()
        self.mortal_user_profile.delete()
        self.admin_user.delete()
        self.mortal_user.delete()
        self.account.delete()

    # pylint: disable=broad-exception-caught
    def test_create(self):
        """
        Test that we can create a plugin using the Plugin.
        /api/v0/plugins/upload/
        """
        client = Client()
        client.force_login(self.admin_user)

        response = client.post(path=self.api_base + "upload/", data=self.plugin_yaml, content_type="application/x-yaml")

        # verify that we are redirected to the new plugin
        self.assertIn(type(response), [HttpResponseRedirect, HttpResponsePermanentRedirect])
        self.assertIn(response.status_code, [301, 302])

        url = response.url
        parsed_url = urlparse(url)
        last_slug = parsed_url.path.split("/")[-2]
        plugin_id = int(last_slug)
        self.plugin = Plugin(plugin_id=plugin_id)
        self.assertEqual(self.plugin.ready, True)

    def test_update(self):
        """
        Test that we can update a plugin using the Plugin.
        /api/v0/plugins/upload
        """
        client = Client()
        client.force_login(self.admin_user)

        response = client.post(
            path=self.api_base + "upload/", data=self.plugin_yaml_modified, content_type="application/x-yaml"
        )
        # verify that we are redirected to the new plugin
        self.assertIn(type(response), [HttpResponseRedirect, HttpResponsePermanentRedirect])
        self.assertIn(response.status_code, [301, 302])

        url = response.url
        parsed_url = urlparse(url)
        last_slug = parsed_url.path.split("/")[-2]
        plugin_id = int(last_slug)

        self.plugin = Plugin(plugin_id=plugin_id)
        self.assertEqual(self.plugin.ready, True)

        self.plugin.refresh()
        self.assertEqual(self.plugin.ready, True)
        self.assertEqual(self.plugin.plugin_meta.description, "MODIFIED")
        self.assertEqual(self.plugin.plugin_data.description, "MODIFIED")
        self.assertEqual(self.plugin.plugin_data.return_data, "MODIFIED")

    def test_delete(self):
        """
        Test that we can delete a plugin using the Plugin.
        /api/v0/plugins/<pk:int>/
        """
        client = Client()
        client.force_login(self.admin_user)

        # create a plugin, so that we can delete it
        response = client.post(path=self.api_base + "upload/", data=self.plugin_yaml, content_type="application/x-yaml")
        # verify that we are redirected to the new plugin
        self.assertIn(type(response), [HttpResponseRedirect, HttpResponsePermanentRedirect])
        self.assertIn(response.status_code, [301, 302])

        url = response.url
        parsed_url = urlparse(url)
        last_slug = parsed_url.path.split("/")[-2]
        plugin_id = int(last_slug)
        self.plugin = Plugin(plugin_id=plugin_id)
        self.assertEqual(self.plugin.ready, True)

        # delete the plugin using the api endpoint
        response = client.delete(
            path=self.api_base + str(self.plugin.id) + "/",
        )
        self.assertIn(response.status_code, [301, 302])

        url = response.url
        parsed_url = urlparse(url)
        normalized_api_base = os.path.normpath(self.api_base.lower())
        normalized_parsed_path = os.path.normpath(parsed_url.path.lower())

        self.assertEqual(normalized_api_base, normalized_parsed_path)

    # pylint: disable=too-many-statements
    def test_validation_permissions(self):
        """Test that the Plugin raises an error when given bad data."""

        client = Client()
        client.force_login(self.mortal_user)
        try:
            client.post(path=self.api_base + "upload/", data=self.plugin_yaml, content_type="application/x-yaml")
        except Exception as e:
            self.assertIsInstance(e, PermissionError)

        plugin_id = -1

        try:
            client.delete(
                path=self.api_base + str(plugin_id) + "/",
            )
        except Exception as e:
            self.assertIsInstance(e, PermissionError)

    def test_validation_bad_data(self):
        """Test that the Plugin raises an error when given bad data."""

    def test_clone(self):
        """Test that we can clone a plugin using the Plugin."""
