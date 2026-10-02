"""Test the LLMHost api, :mod:`smarter.apps.llmhost.api.v1.views.views`."""

from http import HTTPStatus

from django.urls import reverse
from rest_framework.test import APIClient

from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.llmhost.api.v1.urls import LLMHostApiV1ReverseViews as Names
from smarter.apps.llmhost.models import LLMHost
from smarter.lib import json

from .base_classes import LLMHostTestBase


def url(name: str, **kwargs) -> str:
    """Return the url of an LLMHost api view."""
    return reverse(f"{Names.namespace}:{name}", kwargs=kwargs)


class TestLLMHostApi(LLMHostTestBase):
    """Test the LLMHost api views, and their permissions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.llmhost = cls.create_llmhost("test_api_llmhost")
        cls.other_admin_user, cls.other_account, cls.other_user_profile = admin_user_factory()
        cls.other_llmhost = cls.create_llmhost("test_api_other_account", user_profile=cls.other_user_profile)

    @classmethod
    def tearDownClass(cls):
        LLMHost.objects.filter(user_profile=cls.other_user_profile).delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)

    def request(self, method: str, path: str, data=None, status: int = HTTPStatus.OK) -> dict:
        """Make a request, assert its status, and return its json."""
        response = getattr(self.client, method)(path, data=data, format="json")
        self.assertEqual(response.status_code, status, response.content)
        return json.loads(response.content) if response.content else {}

    def test_list(self):
        """Test that the list includes the account's LLMHosts, and not another account's."""
        self.client.force_login(self.non_admin_user)
        data = self.request("get", url(Names.list_view))
        items = data["results"] if isinstance(data, dict) and "results" in data else data
        names = [item["name"] for item in items]
        self.assertIn(self.llmhost.name, names)
        self.assertNotIn(self.other_llmhost.name, names)

    def test_detail(self):
        """Test the detail view, by hashed id and by id, and that another account's LLMHost is not found."""
        data = self.request("get", url(Names.llmhost_by_hashed_id, hashed_id=self.llmhost.hashed_id))
        self.assertEqual(data["name"], self.llmhost.name)
        self.assertEqual(
            self.request("get", url(Names.llmhost_by_id, llmhost_id=self.llmhost.pk))["name"], self.llmhost.name
        )
        # the admin user is a superuser, who may read every account's LLMHosts.
        self.client.force_login(self.non_admin_user)
        self.request("get", url(Names.llmhost_by_id, llmhost_id=self.other_llmhost.pk), status=HTTPStatus.NOT_FOUND)

    def test_unauthenticated(self):
        self.client.logout()
        response = self.client.get(url(Names.list_view))
        self.assertIn(response.status_code, (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN))

    def test_lifecycle(self):
        """Test plan, deploy, status, logs and undeploy."""
        kwargs = {"hashed_id": self.llmhost.hashed_id}
        plan = self.request("get", url(Names.plan_by_hashed_id, **kwargs))
        self.assertIn("Deployment", [r["kind"] for r in plan["resources"]])
        deployed = self.request("post", url(Names.deploy_by_hashed_id, **kwargs), status=HTTPStatus.ACCEPTED)
        self.assertEqual(deployed["status"], "provisioning")
        self.simulate_ready(self.llmhost)
        status = self.request("get", url(Names.status_by_hashed_id, **kwargs))
        self.assertEqual((status["status"], status["readyReplicas"]), ("active", 1))
        self.cluster.pod_logs = "INFO started"
        self.assertEqual(self.request("get", url(Names.logs_by_hashed_id, **kwargs))["logs"], "INFO started")
        self.request("get", url(Names.logs_by_hashed_id, **kwargs) + "?tail=x", status=HTTPStatus.BAD_REQUEST)
        undeployed = self.request("post", url(Names.undeploy_by_hashed_id, **kwargs) + "?purge=true")
        self.assertEqual(undeployed["status"], "inactive")
        self.assertEqual(self.cluster.resources, {})

    def test_cluster_unavailable(self):
        """Test that an unavailable cluster is 503."""
        self.cluster.ready = False
        self.request("post", url(Names.deploy_by_id, llmhost_id=self.llmhost.pk), status=HTTPStatus.SERVICE_UNAVAILABLE)
        self.request("get", url(Names.logs_by_id, llmhost_id=self.llmhost.pk), status=HTTPStatus.SERVICE_UNAVAILABLE)

    def test_owner_only(self):
        """Test that a user who may read, but not own, an LLMHost cannot deploy it, nor read its logs."""
        self.client.force_login(self.non_admin_user)
        kwargs = {"llmhost_id": self.llmhost.pk}
        self.request("get", url(Names.llmhost_by_id, **kwargs))
        self.request("post", url(Names.deploy_by_id, **kwargs), status=HTTPStatus.NOT_FOUND)
        self.request("get", url(Names.logs_by_id, **kwargs), status=HTTPStatus.NOT_FOUND)
        self.request("delete", url(Names.llmhost_by_id, **kwargs), status=HTTPStatus.NOT_FOUND)

    def test_report(self):
        """Test that the report covers the LLMHosts that the user owns."""
        data = self.request("get", url(Names.report))
        self.assertIn(self.llmhost.name, [host["name"] for host in data["llmhosts"]])
        self.client.force_login(self.non_admin_user)
        names = [host["name"] for host in self.request("get", url(Names.report))["llmhosts"]]
        self.assertNotIn(self.other_llmhost.name, names)

    def test_discover(self):
        """Test discovery in the builtin catalog, which needs no network."""
        data = self.request("get", url(Names.discover) + "?catalog=builtin&task=embedding")
        self.assertTrue(data["models"])
        self.assertTrue(all(model["task"] == "embedding" for model in data["models"]))
        self.request("get", url(Names.discover) + "?catalog=nope", status=HTTPStatus.SERVICE_UNAVAILABLE)
        self.request("get", url(Names.discover) + "?limit=x", status=HTTPStatus.BAD_REQUEST)
        manifest = self.request("get", url(Names.discover_manifest) + "?catalog=builtin&repository=BAAI/bge-m3")
        self.assertEqual(manifest["manifest"]["metadata"]["name"], "bge_m3")
        self.request("get", url(Names.discover_manifest), status=HTTPStatus.BAD_REQUEST)

    def test_delete(self):
        llmhost = self.new_llmhost("test_api_delete")
        self.request(
            "delete", url(Names.llmhost_by_hashed_id, hashed_id=llmhost.hashed_id), status=HTTPStatus.NO_CONTENT
        )
        self.assertFalse(LLMHost.objects.filter(pk=llmhost.pk).exists())
