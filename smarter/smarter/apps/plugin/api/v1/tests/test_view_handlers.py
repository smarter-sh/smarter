"""Test the error branches of the plugin api handlers in :mod:`smarter.apps.plugin.api.v1.views`."""

from http import HTTPStatus
from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError
from django.test import RequestFactory

from smarter.apps.account.models import UserProfile
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.plugin.api.v1 import views
from smarter.apps.plugin.models import PluginMeta
from smarter.lib import json

MODULE = "smarter.apps.plugin.api.v1.views"


class TestPluginViewHandlers(TestAccountMixin):
    """Test get_plugin, create_plugin, update_plugin and delete_plugin, with the plugin layer patched."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def request(self, method: str = "get", body=None, path: str = "/api/v1/plugins/1/"):
        content = json.dumps(body) if isinstance(body, (dict, list)) else (body or "")
        request = getattr(self.factory, method)(path, data=content, content_type="application/json")
        request.user = self.admin_user
        return request

    def patch(self, target: str, **kwargs) -> MagicMock:
        patcher = patch(f"{MODULE}.{target}", **kwargs)
        mock = patcher.start()
        self.addCleanup(patcher.stop)
        return mock

    def controller(self, plugin=None, error=None) -> MagicMock:
        """Patch PluginController to return the given plugin, or to raise the given error."""
        if error is not None:
            return self.patch("PluginController", side_effect=error)
        return self.patch("PluginController", return_value=MagicMock(plugin=plugin))

    def patch_plugin_meta(self, **kwargs) -> MagicMock:
        return self.patch("PluginMeta.get_cached_object", **kwargs)

    def no_user_profile(self):
        self.patch("UserProfile.get_cached_object", side_effect=UserProfile.DoesNotExist)

    def assertStatus(self, response, status: int):
        self.assertEqual(response.status_code, status, getattr(response, "content", b"")[:300])

    # -------------------------------------------------------------------------
    # get_plugin
    # -------------------------------------------------------------------------
    def test_get_plugin(self):
        """A ready plugin is returned as json, and anything else is an error."""
        self.patch_plugin_meta(return_value=MagicMock())
        self.controller(plugin=MagicMock(ready=True, to_json=MagicMock(return_value={"name": "x"})))
        self.assertStatus(views.get_plugin(self.request(), 1), HTTPStatus.OK)

    def test_get_plugin_errors(self):
        """Get_plugin maps each failure to its status."""
        self.patch_plugin_meta(return_value=MagicMock())
        cases = (
            ({"plugin": MagicMock(ready=False)}, HTTPStatus.INTERNAL_SERVER_ERROR),
            ({"plugin": None}, HTTPStatus.INTERNAL_SERVER_ERROR),
            ({"error": PluginMeta.DoesNotExist()}, HTTPStatus.NOT_FOUND),
            ({"error": ValidationError("invalid")}, HTTPStatus.BAD_REQUEST),
        )
        for kwargs, status in cases:
            with self.subTest(kwargs=kwargs):
                self.controller(**kwargs)
                self.assertStatus(views.get_plugin(self.request(), 1), status)

    def test_get_plugin_without_a_user_profile(self):
        """Get_plugin is not found without a user profile."""
        self.no_user_profile()
        self.assertStatus(views.get_plugin(self.request(), 1), HTTPStatus.NOT_FOUND)

    # -------------------------------------------------------------------------
    # create_plugin
    # -------------------------------------------------------------------------
    def test_create_plugin(self):
        """A created plugin redirects to its api url."""
        self.controller(plugin=MagicMock(id=42))
        response = views.create_plugin(self.request("post"), data={"kind": "Plugin"})
        self.assertStatus(response, HTTPStatus.FOUND)
        self.assertTrue(response.url.endswith("/api/v1/plugins/42/"))

    def test_create_plugin_errors(self):
        """Create_plugin maps each failure to its status."""
        cases = (
            ({"plugin": None}, HTTPStatus.INTERNAL_SERVER_ERROR),
            ({"error": ValidationError("invalid")}, HTTPStatus.BAD_REQUEST),
        )
        for kwargs, status in cases:
            with self.subTest(kwargs=kwargs):
                self.controller(**kwargs)
                self.assertStatus(views.create_plugin(self.request("post"), data={"kind": "Plugin"}), status)

    def test_create_plugin_request_data(self):
        """Without data, the request's data must be a dict."""
        request = self.request("post")
        request.data = ["not", "a", "dict"]
        self.assertStatus(views.create_plugin(request), HTTPStatus.BAD_REQUEST)
        request = self.request("post")
        self.assertStatus(views.create_plugin(request), HTTPStatus.BAD_REQUEST)

    def test_create_plugin_without_a_user_profile(self):
        """Create_plugin is unauthorized without a user profile."""
        self.no_user_profile()
        self.assertStatus(views.create_plugin(self.request("post"), data={}), HTTPStatus.UNAUTHORIZED)

    # -------------------------------------------------------------------------
    # update_plugin
    # -------------------------------------------------------------------------
    def test_update_plugin_without_a_user(self):
        """Update_plugin is unauthorized without a user or user profile."""
        self.patch("get_resolved_user", return_value=None)
        self.assertStatus(views.update_plugin(self.request("patch", {})), HTTPStatus.UNAUTHORIZED)

    def test_update_plugin_without_a_user_profile(self):
        """Update_plugin is unauthorized when the user has no profile."""
        self.no_user_profile()
        self.assertStatus(views.update_plugin(self.request("patch", {})), HTTPStatus.UNAUTHORIZED)
        self.patch("UserProfile.get_cached_object", return_value=None)
        self.assertStatus(views.update_plugin(self.request("patch", {})), HTTPStatus.UNAUTHORIZED)

    def test_update_plugin_invalid_data(self):
        """Update_plugin rejects bodies that aren't a manifest of a plugin kind."""
        for body in ("", "[1, 2]", "{bad yaml: [", {"kind": "NotAPlugin", "metadata": {"name": "x"}}):
            with self.subTest(body=body):
                self.assertStatus(views.update_plugin(self.request("patch", body)), HTTPStatus.BAD_REQUEST)

    def test_update_plugin_not_found(self):
        """Update_plugin is not found for an unknown plugin id or name."""
        body = {"kind": "Plugin", "metadata": {"name": f"no_such_plugin_{self.hash_suffix}"}}
        self.assertStatus(views.update_plugin(self.request("patch", body)), HTTPStatus.NOT_FOUND)
        self.patch_plugin_meta(side_effect=PluginMeta.DoesNotExist)
        self.assertStatus(views.update_plugin(self.request("patch", body), plugin_id=1), HTTPStatus.NOT_FOUND)

    def test_update_plugin_name_mismatch(self):
        """Update_plugin rejects a manifest whose name isn't the plugin's."""
        plugin_meta = MagicMock()
        plugin_meta.name = "the_plugin"
        self.patch_plugin_meta(return_value=plugin_meta)
        body = {"kind": "Plugin", "metadata": {"name": "another_plugin"}}
        self.assertStatus(views.update_plugin(self.request("patch", body), plugin_id=1), HTTPStatus.BAD_REQUEST)

    def test_update_plugin_invalid_manifest(self):
        """A manifest that fails validation is an internal error."""
        plugin_meta = MagicMock()
        plugin_meta.name = "the_plugin"
        self.patch_plugin_meta(return_value=plugin_meta)
        body = {"kind": "Plugin", "metadata": {"name": "the_plugin"}}
        self.assertStatus(
            views.update_plugin(self.request("patch", body), plugin_id=1), HTTPStatus.INTERNAL_SERVER_ERROR
        )

    # -------------------------------------------------------------------------
    # delete_plugin
    # -------------------------------------------------------------------------
    def test_delete_plugin(self):
        """A deleted plugin redirects to the plugins list."""
        self.patch_plugin_meta(return_value=MagicMock())
        plugin = MagicMock()
        self.controller(plugin=plugin)
        self.assertStatus(views.delete_plugin(self.request("delete"), 1), HTTPStatus.FOUND)
        plugin.delete.assert_called_once()

    def test_delete_plugin_errors(self):
        """Delete_plugin maps each failure to its status."""
        self.patch_plugin_meta(return_value=MagicMock())
        failing = MagicMock()
        failing.delete.side_effect = RuntimeError("delete failed")
        cases = (
            ({"plugin": failing}, HTTPStatus.INTERNAL_SERVER_ERROR),
            ({"plugin": None}, HTTPStatus.INTERNAL_SERVER_ERROR),
            ({"error": PluginMeta.DoesNotExist()}, HTTPStatus.NOT_FOUND),
        )
        for kwargs, status in cases:
            with self.subTest(kwargs=kwargs):
                self.controller(**kwargs)
                self.assertStatus(views.delete_plugin(self.request("delete"), 1), status)

    def test_delete_plugin_without_a_user_profile(self):
        """Delete_plugin is unauthorized without a user profile."""
        self.no_user_profile()
        self.assertStatus(views.delete_plugin(self.request("delete"), 1), HTTPStatus.UNAUTHORIZED)

    # -------------------------------------------------------------------------
    # parse_yaml_file
    # -------------------------------------------------------------------------
    def test_parse_yaml_file(self):
        """Dicts and lists pass through, strings are parsed as YAML."""
        self.assertEqual(views.PluginUploadView.parse_yaml_file({"a": 1}), {"a": 1})
        self.assertEqual(views.PluginUploadView.parse_yaml_file("a: 1"), {"a": 1})
