"""
Test :mod:`smarter.apps.vectorsearch.toolkit`: an LLMClient's Vectorsearches, as tools that the LLM calls.

The vectorstore is in-memory Qdrant, with fake embeddings and a fake cluster.
"""

from unittest.mock import patch

from smarter.apps.account.models.budget import SmarterBudgetExceeded
from smarter.apps.vectorsearch.models import Vectorsearch
from smarter.apps.vectorsearch.toolkit import (
    FUNCTION_NAME_PREFIX,
    VectorsearchToolkit,
    function_name_for,
)
from smarter.apps.vectorstore.tests.base_classes import VectorstoreTestBase
from smarter.common.exceptions import SmarterException


class TestVectorsearchToolkit(VectorstoreTestBase):
    """A Vectorsearch tool's definition, and its calls."""

    def setUp(self):
        super().setUp()
        self.vectorstore_service = self.ready_service("test_vectorsearch_toolkit")
        self.vectorstore = self.vectorstore_service.vectorstore
        for name, topic in (("a.txt", "Smarter manifests describe AI applications. "), ("b.txt", "Cats sleep. ")):
            document, _ = self.vectorstore_service.add_document(name=name, text=topic * 20, metadata={"topic": name})
            self.vectorstore_service.load_document(document)
        self.vectorsearch = Vectorsearch.objects.create(
            name=f"test_vectorsearch_toolkit_{self.hash_suffix}",
            description="Searches the Smarter handbook.",
            user_profile=self.user_profile,
            vectorstore=self.vectorstore,
            k=2,
        )
        self.addCleanup(Vectorsearch.objects.filter(pk=self.vectorsearch.pk).delete)
        self.function_name = function_name_for(self.vectorsearch)
        self.toolkit = VectorsearchToolkit([self.vectorsearch], service_class=self.service_for)

    def service_for(self, vectorstore):
        """Return the in-memory service of the test's vectorstore."""
        self.assertEqual(vectorstore.pk, self.vectorstore.pk)
        return self.vectorstore_service

    def test_tool(self):
        """Each Vectorsearch is one function tool, with its description and one required argument, query."""
        self.assertEqual(self.function_name, f"{FUNCTION_NAME_PREFIX}{self.vectorsearch.pk}")
        tools = self.toolkit.tools
        self.assertEqual(len(tools), 1)
        function = tools[0]["function"]
        self.assertEqual(tools[0]["type"], "function")
        self.assertEqual(function["name"], self.function_name)
        self.assertEqual(function["description"], "Searches the Smarter handbook.")
        self.assertEqual(function["parameters"]["required"], ["query"])
        self.assertEqual(list(function["parameters"]["properties"]), ["query"])
        self.assertTrue(self.toolkit.is_vectorsearch_function(self.function_name))
        self.assertFalse(self.toolkit.is_vectorsearch_function("smarter_plugin_1"))
        self.assertEqual(self.toolkit.vectorsearch_for(self.function_name), self.vectorsearch)
        self.assertIsNone(self.toolkit.vectorsearch_for("smarter_plugin_1"))

    def test_a_vectorsearch_without_a_description_names_its_vectorstore(self):
        """The LLM needs a description to decide when to search, so one is made from the vectorstore's name."""
        Vectorsearch.objects.filter(pk=self.vectorsearch.pk).update(description="")
        self.vectorsearch.refresh_from_db()
        toolkit = VectorsearchToolkit([self.vectorsearch], service_class=self.service_for)
        description = toolkit.tools[0]["function"]["description"]
        self.assertIn(self.vectorstore.name, description)

    def test_call(self):
        """A call returns the Vectorsearch's k results, most similar first, with the names of both resources."""
        result = self.toolkit.call(self.function_name, {"query": "manifests"})
        assert isinstance(result, dict)
        self.assertEqual(result["vectorsearch"], self.vectorsearch.name)
        self.assertEqual(result["vectorstore"], self.vectorstore.name)
        results = result["results"]
        assert isinstance(results, list)
        self.assertEqual(len(results), 2)
        first = results[0]
        assert isinstance(first, dict)
        self.assertIn("text", first)
        self.assertIn("metadata", first)
        self.assertIn("score", first)

    def test_call_with_json_arguments(self):
        """The LLM's arguments may arrive as the JSON string of its tool call."""
        result = self.toolkit.call(self.function_name, '{"query": "manifests"}')
        assert isinstance(result, dict)
        self.assertEqual(result["vectorsearch"], self.vectorsearch.name)

    def test_errors_are_results(self):
        """Every error is a result, {"error": ...}, so that the LLM can recover."""
        cases = (
            ("smarter_vectorsearch_0", {"query": "manifests"}, "is not a vectorsearch tool"),
            (self.function_name, "{not json", "not a JSON object"),
            (self.function_name, {"query": "  "}, "needs a query"),
            (self.function_name, None, "needs a query"),
        )
        for function_name, arguments, message in cases:
            with self.subTest(function_name=function_name, arguments=arguments):
                result = self.toolkit.call(function_name, arguments)
                assert isinstance(result, dict)
                self.assertIn(message, str(result["error"]))

    def test_a_disabled_vectorsearch_is_not_run(self):
        """A Vectorsearch that is disabled after the prompt began is refused, as the REST api refuses it."""
        Vectorsearch.objects.filter(pk=self.vectorsearch.pk).update(is_enabled=False)
        self.vectorsearch.refresh_from_db()
        result = self.toolkit.call(self.function_name, {"query": "manifests"})
        assert isinstance(result, dict)
        self.assertIn("is disabled", str(result["error"]))

    def test_a_budget_refuses_the_search(self):
        """A budget that locks the Vectorsearch refuses the search, and its message is the result."""
        refusal = SmarterBudgetExceeded("The handbook's budget is spent.", self.vectorsearch.record_locator)
        with patch("smarter.apps.vectorsearch.run.charge_authorization", side_effect=refusal) as charge:
            result = self.toolkit.call(self.function_name, {"query": "manifests"})
        self.assertEqual(result, {"error": "The handbook's budget is spent."})
        locators = charge.call_args.args[0]
        self.assertIn(self.vectorsearch.record_locator, locators)

    def test_a_failed_search_is_an_error(self):
        """A search that fails, e.g. of a vectorstore that isn't ready, is reported, not raised."""

        class FailingService:  # pylint: disable=too-few-public-methods
            """A service whose search fails."""

            def __init__(self, vectorstore):
                self.vectorstore = vectorstore

            def search(self, **kwargs):
                """Fail."""
                raise SmarterException("the vectorstore is not ready")

        toolkit = VectorsearchToolkit([self.vectorsearch], service_class=FailingService)
        result = toolkit.call(self.function_name, {"query": "manifests"})
        assert isinstance(result, dict)
        self.assertIn("the vectorstore is not ready", str(result["error"]))
