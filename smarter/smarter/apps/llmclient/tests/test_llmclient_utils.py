"""Test :mod:`smarter.apps.llmclient.models.utils`: the cached resolution of a request to its LLMClient, and its tool counts."""

from unittest.mock import MagicMock, patch

from django.db import connection
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import (
    LLMClient,
    LLMClientExtensions,
    LLMClientPlugin,
)
from smarter.apps.llmclient.models.utils import (
    LLMCLIENT_HOST_PATHS,
    LLMClientToolCounts,
    get_cached_llmclient_by_request,
    get_cached_llmclient_tool_counts,
    invalidate_cached_llmclient_by_hosts,
    invalidate_cached_llmclient_tool_counts,
)
from smarter.apps.llmclient.serializers import (
    LLMClientConfigSerializer,
    LLMClientSerializer,
)
from smarter.apps.llmtool.models import Extension, PluginMeta

HELPER = "smarter.apps.llmclient.models.utils.LLMClientHelper"


class TestGetCachedLLMClientByRequest(TestAccountMixin):
    """Test that the resolution caches hits by host and path, never caches misses, and reads the LLMClient fresh."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(name=f"test_utils_{self.hash_suffix}", user_profile=self.user_profile)
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)
        self.host = f"utils-{self.hash_suffix}.{self.account.account_number}.api.example.com"
        self.addCleanup(self.invalidate)

    def invalidate(self):
        with patch.object(LLMClient, "default_host", new=self.host):
            invalidate_cached_llmclient_by_hosts(self.llmclient)

    def request(self, path: str = "/config/", query: str = ""):
        return RequestFactory().post(f"{path}{query}", HTTP_HOST=self.host)

    def test_none_without_a_request(self):
        self.assertIsNone(get_cached_llmclient_by_request(None))  # type: ignore[arg-type]

    def test_a_miss_is_not_cached(self):
        """A host that no LLMClient serves resolves as soon as one does."""
        with patch(HELPER) as helper:
            helper.return_value.llmclient = None
            self.assertIsNone(get_cached_llmclient_by_request(self.request()))
            helper.return_value.llmclient = self.llmclient
            self.assertEqual(get_cached_llmclient_by_request(self.request()), self.llmclient)
            self.assertEqual(helper.call_count, 2)

    def test_a_hit_is_cached_by_host_and_path_without_the_query_string(self):
        with patch(HELPER) as helper:
            helper.return_value.llmclient = self.llmclient
            get_cached_llmclient_by_request(self.request(query="?session_key=a"))
            get_cached_llmclient_by_request(self.request(query="?session_key=b"))
            self.assertEqual(helper.call_count, 1)

    def test_the_llmclient_is_read_fresh(self):
        """Only the id is cached, so a change, e.g. a deployment by update(), is seen at once."""
        with patch(HELPER) as helper:
            helper.return_value.llmclient = self.llmclient
            self.assertFalse(get_cached_llmclient_by_request(self.request()).deployed)
            LLMClient.objects.filter(pk=self.llmclient.pk).update(deployed=True)
            self.assertTrue(get_cached_llmclient_by_request(self.request()).deployed)
            LLMClient.objects.filter(pk=self.llmclient.pk).delete()
            self.assertIsNone(get_cached_llmclient_by_request(self.request()))

    def test_invalidate_cached_llmclient_by_hosts(self):
        with patch(HELPER) as helper:
            helper.return_value.llmclient = self.llmclient
            for path in LLMCLIENT_HOST_PATHS:
                get_cached_llmclient_by_request(self.request(path))
            self.assertEqual(helper.call_count, len(LLMCLIENT_HOST_PATHS))
            self.invalidate()
            get_cached_llmclient_by_request(self.request())
            self.assertEqual(helper.call_count, len(LLMCLIENT_HOST_PATHS) + 1)

    def test_invalidate_tolerates_an_llmclient_without_hosts(self):
        llmclient = MagicMock(spec=LLMClient)
        type(llmclient).default_host = property(lambda self: (_ for _ in ()).throw(ValueError("no account")))
        llmclient.custom_host = None
        invalidate_cached_llmclient_by_hosts(llmclient)

    def test_a_deleted_llmclient_is_resolved_again(self):
        other = LLMClient.objects.create(name=f"test_utils_other_{self.hash_suffix}", user_profile=self.user_profile)
        self.addCleanup(LLMClient.objects.filter(pk=other.pk).delete)
        with patch(HELPER) as helper:
            helper.return_value.llmclient = self.llmclient
            self.assertEqual(get_cached_llmclient_by_request(self.request()), self.llmclient)
            LLMClient.objects.filter(pk=self.llmclient.pk).delete()
            helper.return_value.llmclient = other
            self.assertEqual(get_cached_llmclient_by_request(self.request()), other)

    def test_other_paths_are_cached_per_user(self):
        """The cli's urls are resolved by the user's LLMClients, so each user has their own resolution."""
        path = f"/api/v1/cli/prompt/{self.llmclient.name}/"
        with patch(HELPER) as helper:
            helper.return_value.llmclient = self.llmclient
            for user in (self.admin_user, self.non_admin_user, self.admin_user):
                request = self.request(path)
                request.user = user
                get_cached_llmclient_by_request(request)
            self.assertEqual(helper.call_count, 2)


class TestGetCachedLLMClientToolCounts(TestAccountMixin):
    """Test that an LLMClient's tools are counted, cached, and counted again when a tool is added or removed."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(
            name=f"test_counts_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)
        self.plugin_meta = PluginMeta.objects.create(
            name=f"test_counts_{self.hash_suffix}",
            plugin_class="static",
            version="1.0.0",
            user_profile=self.user_profile,
        )
        self.addCleanup(PluginMeta.objects.filter(pk=self.plugin_meta.pk).delete)
        self.extension = Extension.objects.create(slug=f"test-counts-{self.hash_suffix}", display_name="Test Counts")
        self.addCleanup(Extension.objects.filter(pk=self.extension.pk).delete)
        self.addCleanup(get_cached_llmclient_tool_counts.invalidate, self.llmclient.pk)  # type: ignore[attr-defined]

    def test_counts(self):
        """Test the counts, and that they are the length of the serializer's tools."""
        self.assertEqual(get_cached_llmclient_tool_counts(self.llmclient.pk), LLMClientToolCounts(0, 0, 0))
        LLMClientPlugin.objects.create(llmclient=self.llmclient, plugin_meta=self.plugin_meta)
        link = LLMClientExtensions.objects.create(llmclient=self.llmclient, extension=self.extension)
        counts = get_cached_llmclient_tool_counts(self.llmclient.pk)
        self.assertEqual(counts, LLMClientToolCounts(extensions=1, plugins=1, mcpclients=0))
        self.assertEqual(counts.total, len(LLMClientSerializer().get_tools(self.llmclient)))
        self.assertEqual(LLMClientConfigSerializer().get_total_tools(self.llmclient), 2)
        link.delete()
        self.assertEqual(get_cached_llmclient_tool_counts(self.llmclient.pk).total, 1)

    def test_cached(self):
        """Test that a second call makes no query."""
        get_cached_llmclient_tool_counts(self.llmclient.pk)
        with CaptureQueriesContext(connection) as queries:
            get_cached_llmclient_tool_counts(self.llmclient.pk)
        self.assertEqual(len(queries), 0, [query["sql"] for query in queries])

    def test_invalidate_without_an_llmclient(self):
        invalidate_cached_llmclient_tool_counts(None)
